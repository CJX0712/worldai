# Author: 晨星
"""Document ingestion: load txt/md/pdf, chunk with sentence-boundary
preference (512 chars / 64 overlap), produce Chunks. MVP supports the
text layer only — no OCR / complex table parsing (out of scope)."""
from __future__ import annotations

import hashlib
import re
import uuid
from pathlib import Path

from .types import Chunk, Document

CHUNK_SIZE = 512
CHUNK_OVERLAP = 64
SUPPORTED_SUFFIXES = {".txt", ".md", ".pdf"}

_SENTENCE_END = re.compile(r"(?<=[。！？；.!?;\n])")


def load_document(path: str | Path) -> Document:
    """Load a document from disk into a Document."""
    p = Path(path)
    if p.suffix.lower() not in SUPPORTED_SUFFIXES:
        raise ValueError(
            f"unsupported file type: {p.suffix} (supported: {sorted(SUPPORTED_SUFFIXES)})"
        )
    if p.suffix.lower() == ".pdf":
        text = _load_pdf(p)
    else:
        text = p.read_text(encoding="utf-8", errors="replace")
    doc_id = hashlib.sha256((str(p.resolve()) + text[:256]).encode()).hexdigest()[:16]
    return Document(id=doc_id, title=p.name, text=text, metadata={"path": str(p)})


def document_from_text(title: str, text: str) -> Document:
    """Build a Document from raw text (API upload path)."""
    doc_id = hashlib.sha256((title + text[:256]).encode()).hexdigest()[:16]
    return Document(id=doc_id, title=title, text=text, metadata={"source": "api"})


def _load_pdf(path: Path) -> str:
    from pypdf import PdfReader  # deferred import

    reader = PdfReader(str(path))
    pages = [(page.extract_text() or "") for page in reader.pages]
    return "\n".join(pages)


def chunk_text(
    text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP
) -> list[str]:
    """Sliding-window chunking with sentence-boundary preference."""
    text = text.strip()
    if not text:
        return []
    if len(text) <= size:
        return [text]
    chunks: list[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + size, n)
        if end < n:
            # Prefer cutting at a sentence boundary within the window.
            window = text[start:end]
            cuts = [m.end() for m in _SENTENCE_END.finditer(window)]
            good = [c for c in cuts if c >= size // 2]
            if good:
                end = start + good[-1]
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= n:
            break
        start = end - overlap
    return chunks


def chunk_document(doc: Document, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[Chunk]:
    """Split a Document into Chunks with stable ids."""
    pieces = chunk_text(doc.text, size=size, overlap=overlap)
    return [
        Chunk(
            id=f"{doc.id}:{i}",
            doc_id=doc.id,
            text=piece,
            metadata={"title": doc.title, "index": i},
        )
        for i, piece in enumerate(pieces)
    ]


def new_session_id() -> str:
    return uuid.uuid4().hex[:12]
