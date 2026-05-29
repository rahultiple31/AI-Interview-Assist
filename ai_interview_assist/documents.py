from pathlib import Path


SUPPORTED_EXTENSIONS = {".txt", ".md", ".csv", ".pdf", ".docx"}


class DocumentReadError(RuntimeError):
    pass


def read_document(path: str | Path) -> str:
    source = Path(path)
    extension = source.suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:
        raise DocumentReadError(
            f"Unsupported file type '{extension}'. Use TXT, MD, CSV, PDF, or DOCX."
        )

    if extension in {".txt", ".md", ".csv"}:
        return _read_text(source)
    if extension == ".pdf":
        return _read_pdf(source)
    if extension == ".docx":
        return _read_docx(source)

    raise DocumentReadError(f"Unsupported file type '{extension}'.")


def _read_text(path: Path) -> str:
    for encoding in ("utf-8", "utf-8-sig", "cp1252"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    raise DocumentReadError(f"Could not read text from {path.name}.")


def _read_pdf(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise DocumentReadError(
            "PDF support requires pypdf. Install dependencies with: pip install -r requirements.txt"
        ) from exc

    try:
        reader = PdfReader(str(path))
        pages = [page.extract_text() or "" for page in reader.pages]
    except Exception as exc:
        raise DocumentReadError(f"Could not read PDF '{path.name}': {exc}") from exc

    return "\n\n".join(page.strip() for page in pages if page.strip())


def _read_docx(path: Path) -> str:
    try:
        from docx import Document
    except ImportError as exc:
        raise DocumentReadError(
            "DOCX support requires python-docx. Install dependencies with: pip install -r requirements.txt"
        ) from exc

    try:
        document = Document(str(path))
        paragraphs = [p.text.strip() for p in document.paragraphs if p.text.strip()]
    except Exception as exc:
        raise DocumentReadError(f"Could not read DOCX '{path.name}': {exc}") from exc

    return "\n".join(paragraphs)
