"""
backend/rag/loader.py - Knowledge Base Document Loader & Text Chunker

Recursively scans knowledge_base/ for .pdf, .docx, .txt, and .md files,
extracts text and metadata, and generates structured text chunks with overlap.
"""

import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

import pypdf
import docx

from backend.config import settings
from backend.utils.logger import get_logger

logger = get_logger("campusai.rag.loader")

# Chunking Configuration Constants
CHUNK_SIZE_CHARS = 500
CHUNK_OVERLAP_CHARS = 80


class DocumentChunk:
    """Class representing a single text chunk with metadata."""

    def __init__(
        self,
        text: str,
        source: str,
        category: str,
        chunk_id: str,
        page: Optional[int] = None,
        last_modified: str = ""
    ) -> None:
        self.text = text
        self.source = source
        self.category = category
        self.chunk_id = chunk_id
        self.page = page
        self.last_modified = last_modified

    def to_dict(self) -> Dict[str, Any]:
        """Convert chunk object to dictionary representation."""
        return {
            "chunk_id": self.chunk_id,
            "text": self.text,
            "source": self.source,
            "category": self.category,
            "page": self.page,
            "last_modified": self.last_modified,
            "char_length": len(self.text)
        }


def read_text_or_md_file(file_path: Path) -> str:
    """Read plaintext or markdown file with fallback encoding handling."""
    for encoding in ["utf-8", "utf-8-sig", "latin-1", "cp1252"]:
        try:
            with open(file_path, "r", encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Unable to decode text file: {file_path}")


def read_pdf_file(file_path: Path) -> List[Dict[str, Any]]:
    """Extract page-by-page text from PDF document."""
    pages_content = []
    reader = pypdf.PdfReader(str(file_path))
    for idx, page in enumerate(reader.pages):
        page_text = page.extract_text() or ""
        if page_text.strip():
            pages_content.append({"page": idx + 1, "text": page_text.strip()})
    return pages_content


def read_docx_file(file_path: Path) -> str:
    """Extract full text paragraphs from DOCX file."""
    doc = docx.Document(str(file_path))
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    return "\n\n".join(paragraphs)


def create_chunks_from_text(
    full_text: str,
    source_filename: str,
    category_name: str,
    last_modified_str: str,
    page_num: Optional[int] = None,
    chunk_size: int = CHUNK_SIZE_CHARS,
    overlap: int = CHUNK_OVERLAP_CHARS
) -> List[DocumentChunk]:
    """
    Split text into ~500 character chunks with 80 character overlap,
    prioritizing paragraph (\n\n) boundaries.
    """
    chunks: List[DocumentChunk] = []
    text_clean = full_text.strip()
    if not text_clean:
        return chunks

    # Primary split by double newlines or headings
    sections = [s.strip() for s in re.split(r'\n\n+|\n(?=#+ )', text_clean) if s.strip()]
    
    current_buffer = ""
    chunk_index = 1

    for sec in sections:
        if len(current_buffer) + len(sec) + 2 <= chunk_size:
            current_buffer = f"{current_buffer}\n\n{sec}".strip() if current_buffer else sec
        else:
            if current_buffer:
                chunk_id = f"{source_filename}_c{chunk_index}"
                chunks.append(
                    DocumentChunk(
                        text=current_buffer,
                        source=source_filename,
                        category=category_name,
                        chunk_id=chunk_id,
                        page=page_num,
                        last_modified=last_modified_str
                    )
                )
                chunk_index += 1

                # Keep overlap characters from end of current_buffer
                if len(current_buffer) > overlap:
                    current_buffer = current_buffer[-overlap:] + "\n\n" + sec
                else:
                    current_buffer = sec
            else:
                current_buffer = sec

    # Flush remaining buffer
    if current_buffer.strip():
        chunk_id = f"{source_filename}_c{chunk_index}"
        chunks.append(
            DocumentChunk(
                text=current_buffer.strip(),
                source=source_filename,
                category=category_name,
                chunk_id=chunk_id,
                page=page_num,
                last_modified=last_modified_str
            )
        )

    return chunks


def load_knowledge_base_documents(kb_dir: Optional[Path] = None) -> List[DocumentChunk]:
    """
    Recursively scan knowledge base directory, load supported files (.pdf, .docx, .txt, .md),
    and extract all document chunks.

    Returns:
        List of DocumentChunk instances.
    """
    target_dir = kb_dir or settings.KNOWLEDGE_BASE_DIR
    if not target_dir.exists():
        logger.warning("Knowledge base directory does not exist: %s", target_dir)
        return []

    logger.info("Scanning knowledge base files in: %s", target_dir)
    all_chunks: List[DocumentChunk] = []
    supported_extensions = {".pdf", ".docx", ".txt", ".md"}

    for root, _, files in os.walk(target_dir):
        for file_name in files:
            file_path = Path(root) / file_name
            ext = file_path.suffix.lower()

            if ext not in supported_extensions:
                continue

            # Determine category (folder name relative to kb_dir)
            rel_path = file_path.relative_to(target_dir)
            category = rel_path.parts[0] if len(rel_path.parts) > 1 else "general"

            # Last modified timestamp
            mtime = os.path.getmtime(file_path)
            last_mod_iso = datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat()

            try:
                if ext in [".txt", ".md"]:
                    content = read_text_or_md_file(file_path)
                    doc_chunks = create_chunks_from_text(
                        full_text=content,
                        source_filename=file_name,
                        category_name=category,
                        last_modified_str=last_mod_iso
                    )
                    all_chunks.extend(doc_chunks)

                elif ext == ".pdf":
                    pages = read_pdf_file(file_path)
                    for p in pages:
                        doc_chunks = create_chunks_from_text(
                            full_text=p["text"],
                            source_filename=file_name,
                            category_name=category,
                            last_modified_str=last_mod_iso,
                            page_num=p["page"]
                        )
                        all_chunks.extend(doc_chunks)

                elif ext == ".docx":
                    content = read_docx_file(file_path)
                    doc_chunks = create_chunks_from_text(
                        full_text=content,
                        source_filename=file_name,
                        category_name=category,
                        last_modified_str=last_mod_iso
                    )
                    all_chunks.extend(doc_chunks)

                logger.info("Loaded document '%s' (Category: %s)", file_name, category)

            except Exception as load_err:
                logger.warning("Skipping corrupt or unreadable file '%s': %s", file_name, str(load_err))

    logger.info("Knowledge base loading complete. Total chunks extracted: %d", len(all_chunks))
    return all_chunks
