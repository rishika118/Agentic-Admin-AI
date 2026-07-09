"""
ingestion/ocr.py — OCR Processor (PaddleOCR)
==============================================

What it does:
    Takes a page from a scanned PDF (where PyMuPDF found no text),
    renders it as an image, then runs PaddleOCR to extract the text.

Why it exists:
    Many official administrative documents from NIT Calicut are scanned
    PDFs — essentially photos of printed pages. PyMuPDF can't read these.
    PaddleOCR can.

OCR Strategy (from the project spec):
    PDF → Has text? → YES → PyMuPDF (fast, accurate)
                   → NO  → PaddleOCR (handles scanned images)

How it connects:
    - Called by ingestion/pipeline.py only for pages flagged needs_ocr=True
      by ingestion/parser.py.
    - Returns extracted text, which is then treated exactly like
      regular PyMuPDF text in the rest of the pipeline.

PaddleOCR Installation Note:
    PaddleOCR requires paddlepaddle as its backend.
    Install with: pip install paddlepaddle paddleocr
    The first run downloads OCR model weights automatically (~8 MB).

    If PaddleOCR is not installed, this module degrades gracefully:
    it returns an empty string with a warning, so the rest of the
    pipeline still works (the page will just be empty).
"""

import io
import fitz   # PyMuPDF — used to render the page as an image

# We try to import PaddleOCR. If it's not installed, we set a flag
# and handle it gracefully rather than crashing the whole server.
try:
    from paddleocr import PaddleOCR
    PADDLEOCR_AVAILABLE = True
except ImportError:
    PADDLEOCR_AVAILABLE = False
    print(
        "[OCR] WARNING: PaddleOCR is not installed.\n"
        "  Scanned pages will be skipped (empty text).\n"
        "  Install with: pip install paddlepaddle paddleocr"
    )

# -------------------------------------------------------------------------
# Module-level OCR instance.
# Creating this once (instead of inside the function) is important because
# PaddleOCR loads model weights on creation — doing it once saves memory.
# -------------------------------------------------------------------------
_ocr_engine = None

def _get_ocr_engine():
    """
    Returns the shared PaddleOCR instance, creating it on first call.
    This is called 'lazy initialization' — we only pay the startup cost
    when OCR is actually needed.
    """
    global _ocr_engine
    if _ocr_engine is None and PADDLEOCR_AVAILABLE:
        print("[OCR] Loading PaddleOCR engine (first-time only, may take a moment)...")
        _ocr_engine = PaddleOCR(
            use_angle_cls=True,   # Detect rotated/upside-down text
            lang="en",            # English language model
            show_log=False,       # Suppress PaddleOCR's verbose logging
        )
        print("[OCR] PaddleOCR engine ready.")
    return _ocr_engine


def ocr_page(pdf_path: str, page_no: int) -> str:
    """
    Run OCR on a single page of a PDF and return the extracted text.

    Args:
        pdf_path : Path to the PDF file.
        page_no  : Page number to OCR (1-indexed, matching parser.py output).

    Returns:
        Extracted text as a single string.
        Returns empty string if PaddleOCR is not available or fails.

    How it works:
        1. Open the PDF with PyMuPDF.
        2. Render the target page as a high-resolution PNG image in memory.
        3. Pass the image bytes to PaddleOCR.
        4. Concatenate all detected text lines and return.
    """
    if not PADDLEOCR_AVAILABLE:
        print(f"[OCR] Skipping page {page_no} — PaddleOCR not installed.")
        return ""

    try:
        ocr = _get_ocr_engine()

        with fitz.open(pdf_path) as doc:
            page = doc[page_no - 1]   # Convert 1-indexed to 0-indexed

            # Render the page as a high-resolution image.
            # Matrix(2, 2) = 2x zoom → 144 DPI instead of 72 DPI.
            # Higher DPI = more detail = better OCR accuracy.
            mat   = fitz.Matrix(2, 2)
            pix   = page.get_pixmap(matrix=mat)

            # Convert to PNG bytes in memory (no temp file needed)
            img_bytes = pix.tobytes("png")

        # PaddleOCR accepts raw bytes wrapped in a BytesIO buffer
        result = ocr.ocr(io.BytesIO(img_bytes), cls=True)

        # PaddleOCR returns a nested list: result[0] is a list of text lines.
        # Each line is: [[bounding_box], [text, confidence_score]]
        if not result or not result[0]:
            print(f"[OCR] Page {page_no}: No text detected.")
            return ""

        lines = []
        for line in result[0]:
            text, confidence = line[1]       # Unpack [text, score]
            if confidence > 0.5:             # Only accept confident detections
                lines.append(text)

        extracted = "\n".join(lines)
        print(f"[OCR] Page {page_no}: Extracted {len(extracted)} chars (OCR)")
        return extracted

    except Exception as e:
        print(f"[OCR] ERROR on page {page_no}: {e}")
        return ""
