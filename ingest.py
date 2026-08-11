"""
SpaceChat ingestion pipeline
----------------------------
Extracts text from a large reference book (e.g. OpenStax Astronomy 2e),
splits it into overlapping chunks tagged with page/section metadata,
embeds each chunk, and stores everything in a local persistent Chroma DB.

Usage:
    python ingest.py --pdf astronomy-2e.pdf --book-title "Astronomy 2e (OpenStax)"

Run this once per book. Re-run with a different --pdf to add more sources
(e.g. a second book, or a folder of supplementary papers) — chunks are
tagged by source so retrieval can cite which book/paper an answer came from.
"""

import argparse
import re
import uuid

import chromadb
import pdfplumber
from sentence_transformers import SentenceTransformer

# --- Config ---------------------------------------------------------------
CHUNK_SIZE_CHARS = 1800       # ~350-450 tokens, good granularity for textbook prose
CHUNK_OVERLAP_CHARS = 250     # keeps context continuous across chunk boundaries
EMBED_MODEL_NAME = "all-MiniLM-L6-v2"   # fast, solid quality, runs locally (no API cost)
CHROMA_DB_PATH = "./chroma_db"
COLLECTION_NAME = "spacechat_docs"

# Matches headers like "1.1 The Nature of Astronomy" — OpenStax's standard
# section-numbering style. Falls back gracefully if a book doesn't use it.
SECTION_HEADER_RE = re.compile(r"^\s*(\d{1,2}\.\d{1,2})\s+([A-Z][^\n]{3,80})\s*$")
CHAPTER_HEADER_RE = re.compile(r"^\s*(?:CHAPTER\s+)?(\d{1,2})\s+([A-Z][^\n]{3,80})\s*$")


def extract_pages(pdf_path):
    """Yields (page_number, text) for every page in the PDF."""
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            yield i, text


def tag_structure(text):
    """Looks for a chapter/section header in a page's text, if present."""
    chapter, section = None, None
    for line in text.splitlines()[:8]:  # headers usually appear near top of page
        sec_match = SECTION_HEADER_RE.match(line)
        if sec_match:
            section = f"{sec_match.group(1)} {sec_match.group(2)}".strip()
        chap_match = CHAPTER_HEADER_RE.match(line)
        if chap_match and len(chap_match.group(2).split()) <= 8:
            chapter = f"Chapter {chap_match.group(1)}: {chap_match.group(2)}".strip()
    return chapter, section


def chunk_text(text, size=CHUNK_SIZE_CHARS, overlap=CHUNK_OVERLAP_CHARS):
    """Simple sliding-window chunker over a block of text."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + size
        chunks.append(text[start:end])
        start += size - overlap
    return chunks


def build_corpus(pdf_path, book_title):
    """Extracts + chunks the PDF, carrying forward the last-seen chapter/section
    across pages so chunks without their own header still get tagged."""
    corpus = []
    current_chapter, current_section = None, None

    for page_num, page_text in extract_pages(pdf_path):
        if not page_text.strip():
            continue

        chapter, section = tag_structure(page_text)
        current_chapter = chapter or current_chapter
        current_section = section or current_section

        for chunk in chunk_text(page_text):
            if len(chunk.strip()) < 50:
                continue  # skip near-empty fragments (page breaks, figure captions alone)
            corpus.append({
                "id": str(uuid.uuid4()),
                "text": chunk,
                "metadata": {
                    "source": book_title,
                    "page": page_num,
                    "chapter": current_chapter or "Unknown",
                    "section": current_section or "Unknown",
                }
            })
    return corpus


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", required=True, help="Path to the source PDF")
    parser.add_argument("--book-title", required=True, help="Display name for citations")
    args = parser.parse_args()

    print(f"Extracting and chunking {args.pdf} ...")
    corpus = build_corpus(args.pdf, args.book_title)
    print(f"Built {len(corpus)} chunks.")

    print(f"Loading embedding model ({EMBED_MODEL_NAME}) ...")
    embedder = SentenceTransformer(EMBED_MODEL_NAME)

    print("Embedding chunks (this can take a few minutes for a full book) ...")
    texts = [c["text"] for c in corpus]
    embeddings = embedder.encode(texts, show_progress_bar=True, batch_size=64).tolist()

    print("Writing to Chroma ...")
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    collection = client.get_or_create_collection(COLLECTION_NAME)

    # Chroma has a batch-size ceiling; write in batches of 500 to be safe
    batch = 500
    for i in range(0, len(corpus), batch):
        chunk_batch = corpus[i:i + batch]
        collection.add(
            ids=[c["id"] for c in chunk_batch],
            documents=[c["text"] for c in chunk_batch],
            embeddings=embeddings[i:i + batch],
            metadatas=[c["metadata"] for c in chunk_batch],
        )

    print(f"Done. {len(corpus)} chunks stored in {CHROMA_DB_PATH}/ under collection '{COLLECTION_NAME}'.")


if __name__ == "__main__":
    main()
