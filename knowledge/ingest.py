"""
knowledge/ingest.py — Asynchronous Document Ingest & Chunking Engine.

Handles:
- Chunking documents into bounded semantic windows with sliding overlap.
- Retaining page, sheet, slide, and line metadata per chunk.
- File hash generation for integrity and caching.
- Asynchronous background ingestion queue so uploads do not block chat.
"""

import os
import re
import hashlib
import logging
import concurrent.futures
from typing import List, Dict, Any, Optional

from tools.file_parser import parse_document

logger = logging.getLogger("chatbot.knowledge.ingest")


def compute_file_hash(file_path: str) -> str:
    """Computes SHA-256 hash of a file for cache invalidation and provenance."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()[:16]


def chunk_text(
    text: str,
    file_name: str,
    page: Optional[int] = None,
    sheet_name: Optional[str] = None,
    chunk_size: int = 700,
    overlap: int = 100
) -> List[Dict[str, Any]]:
    """
    Splits text into chunks respecting sentence/paragraph boundaries where possible.
    """
    clean_text = text.strip()
    if not clean_text:
        return []

    if len(clean_text) <= chunk_size:
        return [{
            "text": clean_text,
            "file_name": file_name,
            "page": page,
            "sheet_name": sheet_name,
            "chunk_idx": 0,
            "char_count": len(clean_text)
        }]

    # Paragraph split
    paragraphs = re.split(r'\n\s*\n', clean_text)
    chunks = []
    current_chunk = ""
    chunk_idx = 0

    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
        if len(current_chunk) + len(p) + 2 <= chunk_size:
            current_chunk = f"{current_chunk}\n\n{p}" if current_chunk else p
        else:
            if current_chunk:
                chunks.append({
                    "text": current_chunk,
                    "file_name": file_name,
                    "page": page,
                    "sheet_name": sheet_name,
                    "chunk_idx": chunk_idx,
                    "char_count": len(current_chunk)
                })
                chunk_idx += 1
                # Take overlap from end
                current_chunk = current_chunk[-overlap:] + "\n" + p
            else:
                # Paragraph itself exceeds chunk_size
                for i in range(0, len(p), chunk_size - overlap):
                    sub = p[i:i + chunk_size]
                    chunks.append({
                        "text": sub,
                        "file_name": file_name,
                        "page": page,
                        "sheet_name": sheet_name,
                        "chunk_idx": chunk_idx,
                        "char_count": len(sub)
                    })
                    chunk_idx += 1
                current_chunk = ""

    if current_chunk.strip():
        chunks.append({
            "text": current_chunk.strip(),
            "file_name": file_name,
            "page": page,
            "sheet_name": sheet_name,
            "chunk_idx": chunk_idx,
            "char_count": len(current_chunk)
        })

    return chunks


class DocumentIngestionPipeline:
    def __init__(self):
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=3)

    def ingest_file_sync(self, file_path: str, file_name: Optional[str] = None) -> Dict[str, Any]:
        """Synchronously parses and chunks a document file."""
        fname = file_name or os.path.basename(file_path)
        fhash = compute_file_hash(file_path)
        raw_sections = parse_document(file_path, fname)

        all_chunks = []
        for sec in raw_sections:
            sec_chunks = chunk_text(
                text=sec["text"],
                file_name=fname,
                page=sec.get("page"),
                sheet_name=sec.get("sheet_name"),
                chunk_size=750,
                overlap=100
            )
            all_chunks.extend(sec_chunks)

        logger.info(f"Ingested '{fname}': {len(raw_sections)} sections, {len(all_chunks)} chunks.")
        return {
            "file_name": fname,
            "file_path": file_path,
            "file_hash": fhash,
            "chunk_count": len(all_chunks),
            "chunks": all_chunks
        }

    def ingest_file_async(self, file_path: str, file_name: Optional[str] = None):
        """Dispatches ingestion to a background worker."""
        return self._executor.submit(self.ingest_file_sync, file_path, file_name)


default_ingest_pipeline = DocumentIngestionPipeline()
