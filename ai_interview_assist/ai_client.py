from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from ai_interview_assist.reference_store import QAMatch, Snippet


class AIClientError(RuntimeError):
    pass


def ai_is_configured() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))


def generate_answer(
    question: str,
    qa_match: QAMatch | None,
    snippets: list[Snippet],
    tone: str,
) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return _local_draft(question, qa_match, snippets, tone)

    return _openai_compatible_answer(question, qa_match, snippets, tone, api_key)


def _openai_compatible_answer(
    question: str,
    qa_match: QAMatch | None,
    snippets: list[Snippet],
    tone: str,
    api_key: str,
) -> str:
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.getenv("AI_INTERVIEW_MODEL", "gpt-4o-mini")
    url = f"{base_url}/chat/completions"

    payload = {
        "model": model,
        "temperature": 0.35,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are an ethical interview preparation assistant. "
                    "Draft concise, truthful, first-person answers using only the provided references. "
                    "Prioritize the supplied question/answer pair when present. "
                    "Do not invent employers, projects, degrees, dates, tools, or metrics."
                ),
            },
            {
                "role": "user",
                "content": _build_prompt(question, qa_match, snippets, tone),
            },
        ],
    }

    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise AIClientError(f"AI request failed with HTTP {exc.code}: {body}") from exc
    except Exception as exc:
        raise AIClientError(f"AI request failed: {exc}") from exc

    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise AIClientError("AI response format was not recognized.") from exc


def _build_prompt(
    question: str,
    qa_match: QAMatch | None,
    snippets: list[Snippet],
    tone: str,
) -> str:
    parts = [
        f"Question:\n{question.strip()}",
        f"Answer style:\n{tone}",
    ]

    if qa_match:
        parts.append(
            "Highest priority reference Q&A:\n"
            f"Reference question: {qa_match.question}\n"
            f"Reference answer: {qa_match.answer}"
        )

    if snippets:
        context = "\n\n".join(
            f"Source: {snippet.source}\n{snippet.text}" for snippet in snippets
        )
        parts.append(f"Resume/document context:\n{context}")
    else:
        parts.append("Resume/document context:\nNo matching reference snippets found.")

    parts.append(
        "Write the answer in 5-8 sentences. If the references are weak, say what "
        "information is missing and provide a safe generic structure."
    )
    return "\n\n".join(parts)


def _local_draft(
    question: str,
    qa_match: QAMatch | None,
    snippets: list[Snippet],
    tone: str,
) -> str:
    if qa_match:
        return (
            f"Reference match found ({qa_match.score:.0%}).\n\n"
            f"{qa_match.answer}\n\n"
            "You can refine this with AI by setting OPENAI_API_KEY before launching the app."
        )

    if snippets:
        bullet_points = "\n".join(
            f"- From {snippet.source}: {snippet.text[:450].strip()}" for snippet in snippets[:3]
        )
        return (
            "No saved Q&A matched strongly, so here is a reference-based draft outline:\n\n"
            f"Question: {question.strip()}\n\n"
            f"Tone: {tone}\n\n"
            "Use these points from your documents:\n"
            f"{bullet_points}\n\n"
            "Suggested structure: start with your direct experience, connect it to the "
            "question, give one specific example, and close with the result or lesson."
        )

    return (
        "No matching saved Q&A or document context was found.\n\n"
        "Add your resume, interview notes, or reference Q&A first, then generate again. "
        "The app is designed to avoid inventing experience that is not in your materials."
    )
