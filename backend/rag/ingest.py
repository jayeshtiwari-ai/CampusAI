"""
backend/rag/ingest.py - CampusAI Vector Index Ingestion Pipeline

Scans knowledge base documents, generates embeddings, builds a FAISS IndexFlatIP vector index,
and persists index binary and metadata JSON files to data/index/.
Detects file changes via content hashing for incremental indexing.
"""

import os
import json
import hashlib
import argparse
from pathlib import Path
from typing import Dict, List, Any, Tuple

import faiss
import numpy as np

from backend.config import settings
from backend.rag.loader import load_knowledge_base_documents, DocumentChunk
from backend.rag.embeddings import get_embedding_manager
from backend.utils.logger import get_logger

logger = get_logger("campusai.rag.ingest")

# Output directory for FAISS index and metadata storage
DATA_INDEX_DIR: Path = settings.BASE_DIR / "data" / "index"
INDEX_FILE_PATH: Path = DATA_INDEX_DIR / "faiss_index.bin"
METADATA_FILE_PATH: Path = DATA_INDEX_DIR / "chunks_metadata.json"
HASHES_FILE_PATH: Path = DATA_INDEX_DIR / "file_hashes.json"


def compute_file_hash(file_path: Path) -> str:
    """Compute MD5 hash of a file's contents."""
    hasher = hashlib.md5()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()


def compute_kb_hashes(kb_dir: Path) -> Dict[str, str]:
    """Compute relative_path -> md5_hash map for all files in knowledge base."""
    hashes = {}
    if not kb_dir.exists():
        return hashes

    for root, _, files in os.walk(kb_dir):
        for f_name in files:
            full_path = Path(root) / f_name
            rel_path = str(full_path.relative_to(kb_dir))
            hashes[rel_path] = compute_file_hash(full_path)
    return hashes


def build_and_save_index(force_rebuild: bool = False) -> None:
    """
    Build FAISS vector index and persist index and metadata to disk.
    
    Args:
        force_rebuild: If True, forces full re-embedding regardless of file hashes.
    """
    DATA_INDEX_DIR.mkdir(parents=True, exist_ok=True)
    kb_dir = settings.KNOWLEDGE_BASE_DIR

    current_hashes = compute_kb_hashes(kb_dir)

    # Check if index exists and hashes match
    if not force_rebuild and INDEX_FILE_PATH.exists() and METADATA_FILE_PATH.exists() and HASHES_FILE_PATH.exists():
        try:
            with open(HASHES_FILE_PATH, "r", encoding="utf-8") as f:
                saved_hashes = json.load(f)
            if saved_hashes == current_hashes:
                logger.info("Knowledge base files unchanged. Skipping re-indexing.")
                print("[✓] FAISS index is already up to date.")
                return
        except Exception as e:
            logger.warning("Failed to verify saved hashes: %s. Rebuilding index.", e)

    logger.info("Starting knowledge base ingestion and index construction...")
    
    # 1. Load document chunks
    chunks: List[DocumentChunk] = load_knowledge_base_documents(kb_dir)
    if not chunks:
        logger.warning("No document chunks loaded from %s!", kb_dir)
        print("[!] No documents found to index.")
        return

    # 2. Extract texts and metadata dictionaries
    chunk_texts = [c.text for c in chunks]
    metadata_list = [c.to_dict() for c in chunks]

    # 3. Generate embeddings
    embed_mgr = get_embedding_manager()
    embeddings = embed_mgr.embed_passages(chunk_texts)

    if len(embeddings) == 0:
        logger.error("Failed to generate embeddings for chunks.")
        return

    # 4. Construct FAISS IndexFlatIP (Cosine similarity on normalized vectors)
    vector_dim = embeddings.shape[1]
    logger.info("Building FAISS IndexFlatIP (Dimension: %d)...", vector_dim)
    index = faiss.IndexFlatIP(vector_dim)
    index.add(embeddings)

    # 5. Persist FAISS index binary
    faiss.write_index(index, str(INDEX_FILE_PATH))
    logger.info("FAISS index saved to %s", INDEX_FILE_PATH)

    # 6. Persist metadata JSON
    with open(METADATA_FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(metadata_list, f, indent=2, ensure_ascii=False)
    logger.info("Chunk metadata saved to %s", METADATA_FILE_PATH)

    # 7. Persist file hashes
    with open(HASHES_FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(current_hashes, f, indent=2)

    # Calculate category summary
    category_counts: Dict[str, int] = {}
    for c in chunks:
        category_counts[c.category] = category_counts.get(c.category, 0) + 1

    print("\n==========================================================")
    print("           CampusAI Knowledge Base Ingestion Summary       ")
    print("==========================================================")
    print(f"Total Chunks Indexed: {len(chunks)}")
    print(f"Embedding Dimension : {vector_dim}")
    print("\nChunks per Category:")
    for cat, count in category_counts.items():
        print(f"  - {cat:<20}: {count} chunks")
    print(f"\nSaved Files:")
    print(f"  - Index Binary : {INDEX_FILE_PATH}")
    print(f"  - Metadata JSON: {METADATA_FILE_PATH}")
    print("==========================================================\n")


def main() -> None:
    """CLI Entrypoint for running ingestion."""
    parser = argparse.ArgumentParser(description="Ingest CampusAI knowledge base documents into FAISS index.")
    parser.add_argument("--rebuild", action="store_true", help="Force complete re-indexing regardless of file hashes.")
    args = parser.parse_args()

    build_and_save_index(force_rebuild=args.rebuild)


if __name__ == "__main__":
    main()
