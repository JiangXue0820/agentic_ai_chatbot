from __future__ import annotations

from io import BytesIO
from typing import List, Dict

import re


def _decode_text(file_bytes: bytes, encoding: str = "utf-8") -> str:
    return BytesIO(file_bytes).read().decode(encoding, errors="ignore")


def extract_text(file_bytes: bytes, filename: str) -> List[Dict[str, str]]:
    """
    Parse supported document types into a list of dicts containing page metadata.
    Returns: [{"page": int, "text": str}]
    """
    filename_lower = filename.lower()

    if filename_lower.endswith(".pdf"):
        from PyPDF2 import PdfReader

        reader = PdfReader(BytesIO(file_bytes))
        pages = []
        for idx, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            pages.append({"page": idx + 1, "text": text.strip()})
        return pages

    if filename_lower.endswith(".docx"):
        from docx import Document

        document = Document(BytesIO(file_bytes))
        text = "\n".join(p.text for p in document.paragraphs)
        return [{"page": 1, "text": text.strip()}]

    if filename_lower.endswith(".md"):
        import markdown

        raw_text = _decode_text(file_bytes)
        html = markdown.markdown(raw_text)
        plain = re.sub(r"<[^>]+>", "", html)
        return [{"page": 1, "text": plain.strip()}]

    if filename_lower.endswith(".txt"):
        text = _decode_text(file_bytes)
        return [{"page": 1, "text": text.strip()}]

    raise ValueError(f"Unsupported file format: {filename}")

