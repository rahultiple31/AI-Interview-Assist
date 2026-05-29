from __future__ import annotations

from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from ai_interview_assist import __app_name__, __version__
from ai_interview_assist.ai_client import AIClientError, ai_is_configured, generate_answer
from ai_interview_assist.documents import SUPPORTED_EXTENSIONS, DocumentReadError, read_document
from ai_interview_assist.reference_store import ReferenceStore
from ai_interview_assist.windows_guard import (
    UnsupportedOperatingSystem,
    ensure_supported_windows,
    windows_display_name,
)


class InterviewAssistApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"{__app_name__} {__version__}")
        self.geometry("1040x720")
        self.minsize(860, 620)

        self.store = ReferenceStore.load()
        self.worker_queue: queue.Queue[tuple[str, str]] = queue.Queue()

        self.status_var = tk.StringVar()
        self.reference_summary_var = tk.StringVar()
        self.ai_status_var = tk.StringVar()
        self.tone_var = tk.StringVar(value="Confident, natural, and concise")
        self.live_auto_var = tk.BooleanVar(value=True)
        self.live_last_question = ""
        self.live_after_id: str | None = None

        self._configure_style()
        self._build_ui()
        self._refresh_summary()
        self._poll_worker_queue()

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        style.configure("Title.TLabel", font=("Segoe UI", 16, "bold"))
        style.configure("Section.TLabel", font=("Segoe UI", 10, "bold"))
        style.configure("Status.TLabel", foreground="#4b5563")

    def _build_ui(self) -> None:
        container = ttk.Frame(self, padding=16)
        container.pack(fill=tk.BOTH, expand=True)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(1, weight=1)

        header = ttk.Frame(container)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        header.columnconfigure(0, weight=1)

        ttk.Label(header, text=__app_name__, style="Title.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            header,
            text=f"{windows_display_name()} | {self._ai_label()}",
            style="Status.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))

        notebook = ttk.Notebook(container)
        notebook.grid(row=1, column=0, sticky="nsew")

        self.live_tab = ttk.Frame(notebook, padding=12)
        self.ask_tab = ttk.Frame(notebook, padding=12)
        self.references_tab = ttk.Frame(notebook, padding=12)
        notebook.add(self.live_tab, text="Realtime")
        notebook.add(self.ask_tab, text="Answer")
        notebook.add(self.references_tab, text="References")

        self._build_live_tab()
        self._build_ask_tab()
        self._build_references_tab()

        footer = ttk.Frame(container)
        footer.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        footer.columnconfigure(0, weight=1)
        ttk.Label(footer, textvariable=self.status_var, style="Status.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            footer,
            text="Use with consent for preparation and drafting.",
            style="Status.TLabel",
        ).grid(row=0, column=1, sticky="e")

    def _build_live_tab(self) -> None:
        self.live_tab.columnconfigure(0, weight=1)
        self.live_tab.columnconfigure(1, weight=1)
        self.live_tab.rowconfigure(1, weight=1)

        transcript_panel = ttk.Frame(self.live_tab)
        transcript_panel.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=(0, 12))
        transcript_panel.columnconfigure(0, weight=1)
        transcript_panel.rowconfigure(2, weight=1)

        ttk.Label(transcript_panel, text="Live Transcript", style="Section.TLabel").grid(
            row=0, column=0, sticky="w"
        )

        live_controls = ttk.Frame(transcript_panel)
        live_controls.grid(row=1, column=0, sticky="ew", pady=(8, 8))
        ttk.Checkbutton(
            live_controls,
            text="Auto draft",
            variable=self.live_auto_var,
        ).pack(side=tk.LEFT)
        ttk.Button(
            live_controls,
            text="Paste Clipboard",
            command=self._paste_live_clipboard,
        ).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(
            live_controls,
            text="Clear",
            command=self._clear_live_transcript,
        ).pack(side=tk.LEFT, padx=(8, 0))

        self.live_transcript_text = tk.Text(
            transcript_panel,
            height=18,
            wrap=tk.WORD,
            font=("Segoe UI", 10),
            undo=True,
        )
        self.live_transcript_text.grid(row=2, column=0, sticky="nsew")
        self.live_transcript_text.bind("<<Modified>>", self._on_live_modified)

        answer_panel = ttk.Frame(self.live_tab)
        answer_panel.grid(row=0, column=1, rowspan=2, sticky="nsew")
        answer_panel.columnconfigure(0, weight=1)
        answer_panel.rowconfigure(3, weight=1)

        ttk.Label(answer_panel, text="Detected Question", style="Section.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        self.live_question_text = tk.Text(
            answer_panel,
            height=5,
            wrap=tk.WORD,
            font=("Segoe UI", 10),
            undo=True,
        )
        self.live_question_text.grid(row=1, column=0, sticky="ew", pady=(8, 10))

        live_answer_controls = ttk.Frame(answer_panel)
        live_answer_controls.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        live_answer_controls.columnconfigure(0, weight=1)
        self.live_generate_button = ttk.Button(
            live_answer_controls,
            text="Draft Now",
            command=self._generate_live_answer,
        )
        self.live_generate_button.grid(row=0, column=1, sticky="e")

        self.live_answer_text = tk.Text(
            answer_panel,
            height=18,
            wrap=tk.WORD,
            font=("Segoe UI", 10),
            undo=True,
        )
        self.live_answer_text.grid(row=3, column=0, sticky="nsew")

    def _build_ask_tab(self) -> None:
        self.ask_tab.columnconfigure(0, weight=1)
        self.ask_tab.rowconfigure(1, weight=1)
        self.ask_tab.rowconfigure(5, weight=2)

        ttk.Label(self.ask_tab, text="Question", style="Section.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        self.question_text = tk.Text(
            self.ask_tab,
            height=6,
            wrap=tk.WORD,
            font=("Segoe UI", 10),
            undo=True,
        )
        self.question_text.grid(row=1, column=0, sticky="nsew", pady=(6, 12))

        controls = ttk.Frame(self.ask_tab)
        controls.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        controls.columnconfigure(1, weight=1)

        ttk.Label(controls, text="Tone").grid(row=0, column=0, sticky="w")
        tone = ttk.Combobox(
            controls,
            textvariable=self.tone_var,
            values=(
                "Confident, natural, and concise",
                "Detailed technical answer",
                "Beginner-friendly explanation",
                "STAR format",
                "Short spoken answer",
            ),
            state="readonly",
            width=34,
        )
        tone.grid(row=0, column=1, sticky="w", padx=(8, 14))

        self.generate_button = ttk.Button(
            controls,
            text="Generate Answer",
            command=self._generate_answer,
        )
        self.generate_button.grid(row=0, column=2, sticky="e")

        ttk.Label(self.ask_tab, textvariable=self.reference_summary_var).grid(
            row=3, column=0, sticky="w", pady=(0, 10)
        )

        ttk.Label(self.ask_tab, text="Answer Draft", style="Section.TLabel").grid(
            row=4, column=0, sticky="w"
        )
        self.answer_text = tk.Text(
            self.ask_tab,
            height=12,
            wrap=tk.WORD,
            font=("Segoe UI", 10),
            undo=True,
        )
        self.answer_text.grid(row=5, column=0, sticky="nsew", pady=(6, 0))

    def _build_references_tab(self) -> None:
        self.references_tab.columnconfigure(0, weight=1)
        self.references_tab.columnconfigure(1, weight=1)
        self.references_tab.rowconfigure(1, weight=1)
        self.references_tab.rowconfigure(4, weight=1)

        left = ttk.Frame(self.references_tab)
        left.grid(row=0, column=0, rowspan=5, sticky="nsew", padx=(0, 14))
        left.columnconfigure(0, weight=1)
        left.rowconfigure(2, weight=1)

        ttk.Label(left, text="Documents", style="Section.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        doc_actions = ttk.Frame(left)
        doc_actions.grid(row=1, column=0, sticky="ew", pady=(8, 8))
        ttk.Button(doc_actions, text="Import File", command=self._import_document).pack(
            side=tk.LEFT
        )
        ttk.Button(
            doc_actions,
            text="Add Pasted Text",
            command=self._add_pasted_reference,
        ).pack(side=tk.LEFT, padx=(8, 0))

        self.document_list = tk.Listbox(left, height=8)
        self.document_list.grid(row=2, column=0, sticky="nsew")

        ttk.Label(left, text="Pasted Reference").grid(
            row=3, column=0, sticky="w", pady=(14, 6)
        )
        self.pasted_reference_text = tk.Text(
            left,
            height=8,
            wrap=tk.WORD,
            font=("Segoe UI", 10),
            undo=True,
        )
        self.pasted_reference_text.grid(row=4, column=0, sticky="nsew")

        right = ttk.Frame(self.references_tab)
        right.grid(row=0, column=1, rowspan=5, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)
        right.rowconfigure(3, weight=1)

        ttk.Label(right, text="Priority Q&A", style="Section.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        self.qa_question_text = tk.Text(
            right,
            height=5,
            wrap=tk.WORD,
            font=("Segoe UI", 10),
            undo=True,
        )
        self.qa_question_text.grid(row=1, column=0, sticky="nsew", pady=(8, 10))

        ttk.Label(right, text="Saved Answer").grid(row=2, column=0, sticky="w")
        self.qa_answer_text = tk.Text(
            right,
            height=10,
            wrap=tk.WORD,
            font=("Segoe UI", 10),
            undo=True,
        )
        self.qa_answer_text.grid(row=3, column=0, sticky="nsew", pady=(6, 10))
        ttk.Button(right, text="Save Q&A", command=self._add_qa).grid(
            row=4, column=0, sticky="e"
        )

    def _refresh_summary(self) -> None:
        qa_count, document_count = self.store.counts()
        self.reference_summary_var.set(
            f"{qa_count} priority Q&A items | {document_count} reference documents"
        )
        self.ai_status_var.set(self._ai_label())

        if hasattr(self, "document_list"):
            self.document_list.delete(0, tk.END)
            for document in self.store.documents:
                self.document_list.insert(tk.END, document["name"])

        self.status_var.set(f"References saved at {self.store.path}")

    def _ai_label(self) -> str:
        return "AI connected" if ai_is_configured() else "Local reference mode"

    def _import_document(self) -> None:
        filetypes = [
            ("Supported documents", " ".join(f"*{ext}" for ext in SUPPORTED_EXTENSIONS)),
            ("All files", "*.*"),
        ]
        selected = filedialog.askopenfilename(title="Import reference", filetypes=filetypes)
        if not selected:
            return

        path = Path(selected)
        try:
            text = read_document(path)
            self.store.add_document(path.name, text, str(path))
        except (DocumentReadError, ValueError) as exc:
            messagebox.showerror("Import failed", str(exc))
            return

        self._refresh_summary()
        self.status_var.set(f"Imported {path.name}")

    def _add_pasted_reference(self) -> None:
        text = self.pasted_reference_text.get("1.0", tk.END).strip()
        if not text:
            messagebox.showwarning("Reference required", "Paste reference text first.")
            return

        name = f"Pasted reference {len(self.store.documents) + 1}"
        try:
            self.store.add_document(name, text)
        except ValueError as exc:
            messagebox.showerror("Save failed", str(exc))
            return

        self.pasted_reference_text.delete("1.0", tk.END)
        self._refresh_summary()
        self.status_var.set(f"Saved {name}")

    def _add_qa(self) -> None:
        question = self.qa_question_text.get("1.0", tk.END)
        answer = self.qa_answer_text.get("1.0", tk.END)
        try:
            self.store.add_qa(question, answer)
        except ValueError as exc:
            messagebox.showwarning("Q&A required", str(exc))
            return

        self.qa_question_text.delete("1.0", tk.END)
        self.qa_answer_text.delete("1.0", tk.END)
        self._refresh_summary()
        self.status_var.set("Saved priority Q&A")

    def _paste_live_clipboard(self) -> None:
        try:
            clipboard_text = self.clipboard_get()
        except tk.TclError:
            messagebox.showwarning("Clipboard empty", "No text was found on the clipboard.")
            return

        if clipboard_text.strip():
            self.live_transcript_text.insert(tk.END, clipboard_text.strip() + "\n")
            self._schedule_live_answer()

    def _clear_live_transcript(self) -> None:
        if self.live_after_id:
            self.after_cancel(self.live_after_id)
            self.live_after_id = None
        self.live_last_question = ""
        self.live_transcript_text.delete("1.0", tk.END)
        self.live_question_text.delete("1.0", tk.END)
        self.live_answer_text.delete("1.0", tk.END)
        self.status_var.set("Realtime transcript cleared")

    def _on_live_modified(self, _event: tk.Event) -> None:
        if not self.live_transcript_text.edit_modified():
            return
        self.live_transcript_text.edit_modified(False)
        if self.live_auto_var.get():
            self._schedule_live_answer()

    def _schedule_live_answer(self) -> None:
        if self.live_after_id:
            self.after_cancel(self.live_after_id)
        self.live_after_id = self.after(1800, self._generate_live_answer)

    def _generate_live_answer(self) -> None:
        self.live_after_id = None
        transcript = self.live_transcript_text.get("1.0", tk.END).strip()
        question = _extract_latest_question(transcript)
        manual_question = self.live_question_text.get("1.0", tk.END).strip()

        if manual_question and not question:
            question = manual_question

        if not question:
            self.status_var.set("Realtime mode is waiting for a question.")
            return

        if question == self.live_last_question and self.live_answer_text.get("1.0", tk.END).strip():
            return

        self.live_last_question = question
        self.live_question_text.delete("1.0", tk.END)
        self.live_question_text.insert(tk.END, question)
        self.live_generate_button.configure(state=tk.DISABLED)
        self.live_answer_text.delete("1.0", tk.END)
        self.live_answer_text.insert(tk.END, "Drafting...\n")
        self.status_var.set("Realtime answer draft in progress...")

        thread = threading.Thread(
            target=self._answer_worker,
            args=(question, self.tone_var.get(), "live_answer"),
            daemon=True,
        )
        thread.start()

    def _generate_answer(self) -> None:
        question = self.question_text.get("1.0", tk.END).strip()
        if not question:
            messagebox.showwarning("Question required", "Enter a question first.")
            return

        self.generate_button.configure(state=tk.DISABLED)
        self.answer_text.delete("1.0", tk.END)
        self.answer_text.insert(tk.END, "Generating...\n")
        self.status_var.set("Searching references and drafting answer...")

        thread = threading.Thread(
            target=self._answer_worker,
            args=(question, self.tone_var.get(), "answer"),
            daemon=True,
        )
        thread.start()

    def _answer_worker(self, question: str, tone: str, event_name: str) -> None:
        try:
            qa_match = self.store.find_best_qa(question)
            snippets = self.store.top_snippets(question)
            answer = generate_answer(question, qa_match, snippets, tone)
        except AIClientError as exc:
            answer = str(exc)
        except Exception as exc:
            answer = f"Could not generate answer: {exc}"

        self.worker_queue.put((event_name, answer))

    def _poll_worker_queue(self) -> None:
        try:
            while True:
                event, payload = self.worker_queue.get_nowait()
                if event == "answer":
                    self.answer_text.delete("1.0", tk.END)
                    self.answer_text.insert(tk.END, payload)
                    self.generate_button.configure(state=tk.NORMAL)
                    self.status_var.set("Answer draft ready")
                elif event == "live_answer":
                    self.live_answer_text.delete("1.0", tk.END)
                    self.live_answer_text.insert(tk.END, payload)
                    self.live_generate_button.configure(state=tk.NORMAL)
                    self.status_var.set("Realtime answer draft ready")
        except queue.Empty:
            pass

        self.after(150, self._poll_worker_queue)


def _extract_latest_question(transcript: str) -> str:
    if not transcript.strip():
        return ""

    lines = [line.strip() for line in transcript.splitlines() if line.strip()]
    for line in reversed(lines):
        if "?" in line:
            return line[-700:].strip()

    recent_text = " ".join(lines)[-700:].strip()
    question_starters = (
        "can you",
        "could you",
        "do you",
        "did you",
        "have you",
        "how ",
        "tell me",
        "what ",
        "when ",
        "where ",
        "why ",
    )
    lowered = recent_text.lower()
    for starter in question_starters:
        index = lowered.rfind(starter)
        if index >= 0:
            return recent_text[index:].strip()

    return recent_text


def main() -> None:
    try:
        ensure_supported_windows()
    except UnsupportedOperatingSystem as exc:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(__app_name__, str(exc))
        root.destroy()
        return

    app = InterviewAssistApp()
    app.mainloop()
