"""
ingestion/chunking.py — Text Chunker
======================================

What it does:
    Takes the full extracted text of a document and splits it into
    smaller, overlapping chunks using LangChain's RecursiveCharacterTextSplitter.

    Each chunk is a short passage (default: 500 characters) with a small
    overlap with the previous chunk (default: 50 characters).

    Also tracks which page number each chunk came from.

Why it exists:
    LLMs have a context window limit — we can't feed an entire 50-page
    PDF in one shot. Chunking solves this by breaking the document into
    pieces that fit within the context window.

    The overlap ensures we don't lose meaning at chunk boundaries.
    Example: if a sentence starts at the end of chunk 1 and ends at the
    beginning of chunk 2, both chunks contain part of that sentence.

How it connects:
    - Called by ingestion/pipeline.py after parser.py + ocr.py produce text.
    - Returns ChunkData objects that are passed to ingestion/embeddings.py.
    - chunk_text and page_no are stored in the `chunks` table.

Configuration (from .env via config.py):
    CHUNK_SIZE    = 500   characters per chunk
    CHUNK_OVERLAP = 50    characters shared between consecutive chunks
"""

from dataclasses import dataclass
from typing import List, Tuple

from langchain_text_splitters import RecursiveCharacterTextSplitter

from config import settings


@dataclass
class ChunkData:
    """
    Represents one text chunk ready for embedding.

    Attributes:
        chunk_index : Position of this chunk within the document (0-based).
        chunk_text  : The actual text content of this chunk.
        page_no     : Page number this chunk came from (1-indexed).
                      Used for citations ("Page 3 of hostel_circular.pdf").
    """
    chunk_index: int
    chunk_text:  str
    page_no:     int


def chunk_document(pages: List[Tuple[int, str]]) -> List[ChunkData]:
    """
    Split document pages into overlapping text chunks.

    Args:
        pages: A list of (page_no, text) tuples. Each tuple represents
               one page from the PDF.

               Example:
                   [(1, "This is page 1 text..."),
                    (2, "This is page 2 text..."),
                    (3, "This is page 3 text...")]

    Returns:
        A list of ChunkData objects, one per chunk.
        Chunks preserve their source page number for citations.

    How page tracking works:
        We concatenate all pages with a special separator that encodes
        the page number: "<<<PAGE:2>>>". After splitting, we scan back
        through the text to figure out which page each chunk came from.
    """
    if not pages:
        return []

    # -------------------------------------------------------------------------
    # Step 1: Build a single combined text with page markers.
    # We need one big string for the splitter, but we want to track pages.
    # The marker "<<<PAGE:N>>>" acts as a breadcrumb.
    # -------------------------------------------------------------------------
    combined_text = ""
    for page_no, text in pages:
        if text.strip():   # Skip empty pages (no text, no OCR result)
            combined_text += f"\n<<<PAGE:{page_no}>>>\n{text}\n"

    if not combined_text.strip():
        print("[Chunking] No text to chunk.")
        return []

    # -------------------------------------------------------------------------
    # Step 2: Split using RecursiveCharacterTextSplitter.
    #
    # "Recursive" means it tries to split on the most natural boundary first:
    #   1. Double newlines (paragraphs) — preferred
    #   2. Single newlines (lines)
    #   3. Spaces (words)
    #   4. Individual characters (last resort)
    # This keeps chunks semantically coherent.
    # -------------------------------------------------------------------------
    splitter = RecursiveCharacterTextSplitter(
        chunk_size    = settings.CHUNK_SIZE,
        chunk_overlap = settings.CHUNK_OVERLAP,
        length_function = len,
        separators    = ["\n\n", "\n", ". ", " ", ""],
    )

    raw_chunks = splitter.split_text(combined_text)

    # -------------------------------------------------------------------------
    # Step 3: For each chunk, figure out which page it came from.
    # We scan backwards through the chunk for the nearest <<<PAGE:N>>> marker.
    # If no marker is in the chunk, we use the last known page.
    # -------------------------------------------------------------------------
    import re
    page_marker_re = re.compile(r"<<<PAGE:(\d+)>>>")

    chunk_results: List[ChunkData] = []
    last_known_page = pages[0][0] if pages else 1   # Default to first page

    for i, raw_chunk in enumerate(raw_chunks):
        # Find all page markers inside this chunk
        matches = page_marker_re.findall(raw_chunk)
        if matches:
            last_known_page = int(matches[-1])   # Use the last marker found

        # Clean the chunk: remove page markers from the actual text
        clean_chunk = page_marker_re.sub("", raw_chunk).strip()

        if not clean_chunk:
            continue   # Skip chunks that are only page markers

        chunk_results.append(ChunkData(
            chunk_index = i,
            chunk_text  = clean_chunk,
            page_no     = last_known_page,
        ))

    print(f"[Chunking] Created {len(chunk_results)} chunks "
          f"(size={settings.CHUNK_SIZE}, overlap={settings.CHUNK_OVERLAP})")

    return chunk_results
