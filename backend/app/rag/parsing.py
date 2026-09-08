"""Turn an uploaded file's raw bytes into plain text."""
import io

from docx import Document as DocxDocument
from pypdf import PdfReader


def extract_text(filename: str, content_type: str | None, raw: bytes) -> str:
    lower = filename.lower()

    if lower.endswith(".pdf") or content_type == "application/pdf":
        reader = PdfReader(io.BytesIO(raw))
        return "\n\n".join(page.extract_text() or "" for page in reader.pages)

    if lower.endswith(".docx"):
        doc = DocxDocument(io.BytesIO(raw))
        return "\n".join(p.text for p in doc.paragraphs)

    # Fallback: treat as plain text (.txt, .md, .csv, etc).
    return raw.decode("utf-8", errors="ignore")
