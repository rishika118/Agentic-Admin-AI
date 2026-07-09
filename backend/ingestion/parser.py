"""
ingestion/parser.py — PDF Text Extractor
==========================================

What it does:
    Opens a PDF file using PyMuPDF (imported as `fitz`) and extracts text
    from every page. For each page, it decides:
        - If the page has readable text → extract it directly (fast, accurate).
        - If the page appears to be a scanned image → flag it for OCR.

    Returns a list of PageResult objects, one per page, containing:
        - page_no   : Page number (1-indexed, for human-readable citations)
        - text      : Extracted text (empty string if needs OCR)
        - needs_ocr : True if the page should go through PaddleOCR

Why it exists:
    This is Step 1 of the ingestion pipeline. Without readable text,
    we cannot chunk, embed, or search anything.

How it connects:
    - Called by ingestion/pipeline.py as the first step.
    - Pages with needs_ocr=True are passed to ingestion/ocr.py.
    - Text from all pages is collected and passed to ingestion/chunking.py.

OCR Decision Logic:
    We consider a page "scanned" (needs OCR) if the total extracted
    text is fewer than MIN_TEXT_LENGTH characters. This handles
    cases like image-only pages or pages where text is embedded in images.
"""

import fitz  # PyMuPDF — imported as 'fitz' (historical name from the library's origin)
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

# A page with fewer than this many characters is treated as scanned/image-only.
MIN_TEXT_LENGTH = 50


@dataclass
class PageResult:
    """
    Holds the result of parsing one PDF page.

    Attributes:
        page_no   : Page number, 1-indexed (matches what users see in a PDF viewer).
        text      : Extracted text content. Empty string if page needs OCR.
        needs_ocr : True if PyMuPDF couldn't find enough text on this page.
    """
    page_no:   int
    text:      str
    needs_ocr: bool = False


def extract_text_from_pdf(file_path: str) -> List[PageResult]:
    """
    Open a PDF and extract text from every page.

    Args:
        file_path: Absolute or relative path to the PDF file.

    Returns:
        A list of PageResult objects, one per page.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError:        If the file is not a valid PDF.

    Example:
        pages = extract_text_from_pdf("storage/uploads/hostel_circular.pdf")
        for page in pages:
            if page.needs_ocr:
                print(f"Page {page.page_no} needs OCR")
            else:
                print(f"Page {page.page_no}: {page.text[:80]}...")
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {file_path}")

    results: List[PageResult] = []

    # fitz.open() opens the PDF. Using 'with' ensures it's closed even on error.
    with fitz.open(str(path)) as doc:
        total_pages = len(doc)
        print(f"[Parser] Opened '{path.name}' — {total_pages} page(s)")

        for page_index in range(total_pages):
            page_no = page_index + 1          # Convert 0-indexed to 1-indexed
            page    = doc[page_index]

            # get_text("text") extracts plain text, preserving line breaks.
            # It returns an empty string if the page has no selectable text.
            raw_text  = page.get_text("text")
            clean_text = raw_text.strip()

            # Decide if this page needs OCR
            needs_ocr = len(clean_text) < MIN_TEXT_LENGTH

            results.append(PageResult(
                page_no   = page_no,
                text      = clean_text,
                needs_ocr = needs_ocr,
            ))

            status = "needs OCR" if needs_ocr else f"{len(clean_text)} chars"
            print(f"  [Parser] Page {page_no}/{total_pages}: {status}")

    return results


def calculate_file_hash(file_path: str) -> str:
    """
    Calculate the SHA-256 hash of a file.

    This is used for deduplication: if a PDF with the same hash already
    exists in the database, we skip processing it again.

    Args:
        file_path: Path to the file.

    Returns:
        A 64-character hex string (SHA-256 hash).

    Example:
        hash_val = calculate_file_hash("storage/uploads/hostel_circular.pdf")
        # → "a3f5d9c1b2e4..."
    """
    import hashlib

    sha256 = hashlib.sha256()
    # Read in chunks to handle large files without loading everything into RAM.
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()
