from __future__ import annotations

import json
import math
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


APP_DIR = Path(os.getenv("APPDATA", str(Path.home() / "AppData" / "Roaming"))) / "AIInterviewAssist"
STORE_PATH = APP_DIR / "references.json"


TOKEN_RE = re.compile(r"[a-zA-Z0-9+#.]+")


@dataclass
class QAMatch:
    question: str
    answer: str
    score: float


@dataclass
class Snippet:
    source: str
    text: str
    score: float


class ReferenceStore:
    def __init__(self, path: Path = STORE_PATH) -> None:
        self.path = path
        self.qa_items: list[dict[str, str]] = []
        self.documents: list[dict[str, str]] = []

    @classmethod
    def load(cls, path: Path = STORE_PATH) -> "ReferenceStore":
        store = cls(path)
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                _backup_invalid_store(path)
                return store
            if not isinstance(data, dict):
                _backup_invalid_store(path)
                return store
            store.qa_items = _clean_qa_items(data.get("qa_items", []))
            store.documents = _clean_documents(data.get("documents", []))
        return store

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "qa_items": self.qa_items,
            "documents": self.documents,
        }
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def add_qa(self, question: str, answer: str) -> None:
        question = question.strip()
        answer = answer.strip()
        if not question or not answer:
            raise ValueError("Question and answer are required.")

        self.qa_items.append({"question": question, "answer": answer})
        self.save()

    def add_document(self, name: str, text: str, path: str = "") -> None:
        text = _compact_text(text)
        if not text:
            raise ValueError("Document did not contain readable text.")

        self.documents.append({"name": name.strip(), "path": path, "text": text})
        self.save()

    def find_best_qa(self, question: str) -> QAMatch | None:
        tokens = _tokens(question)
        if not tokens:
            return None

        normalized_question = _normalize(question)
        best: QAMatch | None = None
        for item in self.qa_items:
            candidate_question = item["question"]
            score = _similarity(tokens, _tokens(candidate_question))
            normalized_candidate = _normalize(candidate_question)

            if normalized_question == normalized_candidate:
                score = 1.0
            elif normalized_question in normalized_candidate or normalized_candidate in normalized_question:
                score = max(score, 0.82)

            if best is None or score > best.score:
                best = QAMatch(candidate_question, item["answer"], score)

        if best and best.score >= 0.42:
            return best
        return None

    def top_snippets(self, question: str, limit: int = 5) -> list[Snippet]:
        query_tokens = _tokens(question)
        if not query_tokens:
            return []

        snippets: list[Snippet] = []
        for document in self.documents:
            chunks = _chunks(document["text"])
            for chunk in chunks:
                score = _similarity(query_tokens, _tokens(chunk))
                if score > 0:
                    snippets.append(Snippet(document["name"], chunk, score))

        snippets.sort(key=lambda item: item.score, reverse=True)
        return snippets[:limit]

    def counts(self) -> tuple[int, int]:
        return len(self.qa_items), len(self.documents)

    def as_dict(self) -> dict[str, Any]:
        return {"qa_items": self.qa_items, "documents": self.documents}


def _clean_qa_items(items: Any) -> list[dict[str, str]]:
    cleaned = []
    if not isinstance(items, list):
        return cleaned

    for item in items:
        if not isinstance(item, dict):
            continue
        question = str(item.get("question", "")).strip()
        answer = str(item.get("answer", "")).strip()
        if question and answer:
            cleaned.append({"question": question, "answer": answer})
    return cleaned


def _clean_documents(items: Any) -> list[dict[str, str]]:
    cleaned = []
    if not isinstance(items, list):
        return cleaned

    for item in items:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip() or "Reference"
        path = str(item.get("path", "")).strip()
        text = _compact_text(str(item.get("text", "")))
        if text:
            cleaned.append({"name": name, "path": path, "text": text})
    return cleaned


def _tokens(text: str) -> set[str]:
    return {token.lower() for token in TOKEN_RE.findall(text)}


def _normalize(text: str) -> str:
    return " ".join(TOKEN_RE.findall(text.lower()))


def _compact_text(text: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", text.replace("\r\n", "\n")).strip()


def _similarity(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0

    overlap = len(left & right)
    if overlap == 0:
        return 0.0
    return overlap / math.sqrt(len(left) * len(right))


def _chunks(text: str, target_size: int = 1200) -> list[str]:
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    chunks: list[str] = []
    current = ""

    for paragraph in paragraphs:
        if len(current) + len(paragraph) + 1 > target_size and current:
            chunks.append(current)
            current = paragraph
        else:
            current = f"{current}\n{paragraph}".strip()

    if current:
        chunks.append(current)

    return chunks


def _backup_invalid_store(path: Path) -> None:
    if not path.exists():
        return

    timestamp = int(time.time())
    backup_path = path.with_name(f"{path.stem}.invalid-{timestamp}{path.suffix}")
    try:
        path.replace(backup_path)
    except OSError:
        pass
