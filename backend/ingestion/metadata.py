"""
ingestion/metadata.py — Document Metadata Extractor
=====================================================

What it does:
    Extracts structured metadata from a PDF's text content:
        - title           : Document heading
        - document_number : e.g., "NITC/AC/2024/001"
        - date            : Issue date
        - department      : Issuing department
        - category        : Document type (Circular, Office Order, etc.)

    Strategy (fast first, LLM fallback):
        1. Try Regex patterns on the first 1-2 pages (fast, no LLM needed).
        2. If key fields are still missing → call Ollama LLM to extract them.

Why it exists:
    PostgreSQL needs structured metadata to make documents searchable and
    filterable. Without metadata, all we have are anonymous blobs of text.

    The "Regex first" strategy avoids unnecessary LLM calls for documents
    with predictable formatting — which most government/institutional PDFs have.

How it connects:
    - Called by ingestion/pipeline.py after parser.py extracts text.
    - Results are stored in the `documents` table via database/postgres.py.
"""

import re
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class DocumentMetadata:
    """
    Holds the extracted metadata for one document.
    All fields are Optional because not every PDF will have all fields.
    """
    title:           Optional[str] = None
    document_number: Optional[str] = None
    date:            Optional[str] = None
    department:      Optional[str] = None
    category:        Optional[str] = None


# ---------------------------------------------------------------------------
# REGEX PATTERNS
# These cover common formats found in NIT Calicut administrative documents.
# We use named groups (?P<name>...) so we can access matches by name.
# ---------------------------------------------------------------------------

# Document number patterns: "No. NITC/AC/2024/001" or "F.No. ..."
_RE_DOC_NUMBER = re.compile(
    r"(?:No\.|F\.No\.|Ref\.|Ref No\.?)\s*[:\-]?\s*([A-Z0-9/\-\.]+)",
    re.IGNORECASE,
)

# Date patterns: "01 January 2024", "01/01/2024", "2024-01-01"
_RE_DATE = re.compile(
    r"\b(\d{1,2}[\s\-/]\w+[\s\-/]\d{4}|\d{4}[\-/]\d{2}[\-/]\d{2})\b"
)

# Category keywords found in document titles or early lines
_CATEGORY_KEYWORDS = {
    "Office Order":   r"\boffice\s+order\b",
    "Circular":       r"\bcircular\b",
    "Notification":   r"\bnotification\b",
    "Notice":         r"\bnotice\b",
    "Guidelines":     r"\bguidelines?\b",
    "Policy":         r"\bpolic(?:y|ies)\b",
    "Regulation":     r"\bregulations?\b",
    "Advertisement":  r"\badvertisement\b",
    "Minutes":        r"\bminutes\s+of\b",
    "Tender":         r"\btender\b",
}

# Known NIT Calicut departments
_DEPARTMENT_KEYWORDS = [
    "Academic Section",
    "Accounts Section",
    "Administration",
    "Computer Centre",
    "Dean Academics",
    "Dean Research",
    "Dean Students",
    "Establishment",
    "Finance",
    "Hostel",
    "Library",
    "PG Section",
    "Registrar",
    "Research",
    "Store Section",
    "UG Section",
]


def extract_metadata_with_regex(text: str) -> DocumentMetadata:
    """
    Extract metadata from text using regular expressions.

    We only look at the first ~2000 characters (roughly the first 1-2 pages)
    because metadata (title, number, date) is almost always at the top.

    Args:
        text: Full text content of the document.

    Returns:
        DocumentMetadata with as many fields filled as regex could find.
    """
    # Limit to top of document for efficiency
    head = text[:2000]
    meta = DocumentMetadata()

    # ---- Document Number ----
    match = _RE_DOC_NUMBER.search(head)
    if match:
        meta.document_number = match.group(1).strip()

    # ---- Date ----
    match = _RE_DATE.search(head)
    if match:
        meta.date = match.group(1).strip()

    # ---- Category ----
    for category, pattern in _CATEGORY_KEYWORDS.items():
        if re.search(pattern, head, re.IGNORECASE):
            meta.category = category
            break

    # ---- Department ----
    for dept in _DEPARTMENT_KEYWORDS:
        if dept.lower() in head.lower():
            meta.department = dept
            break

    # ---- Title ----
    # Use the first non-empty line that is reasonably long (likely the heading)
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    for line in lines[:10]:                        # Only check first 10 lines
        if 10 < len(line) < 300:                   # Reasonable title length
            # Skip lines that look like addresses or page markers
            if not re.match(r"^(page\s*\d+|www\.|http|nitc\.ac\.in)", line, re.IGNORECASE):
                meta.title = line
                break

    return meta


def extract_metadata_with_llm(text: str, filename: str) -> DocumentMetadata:
    """
    Use the Ollama LLM to extract metadata when regex is insufficient.

    This is the fallback path — only called if regex couldn't fill the
    important fields (title is the most critical one).

    Args:
        text     : Document text (we send only the first ~1500 chars).
        filename : PDF filename as a last-resort title hint.

    Returns:
        DocumentMetadata populated by the LLM.
    """
    try:
        from langchain_ollama import OllamaLLM
        from config import settings

        llm = OllamaLLM(
            model=settings.OLLAMA_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
        )

        # We send only the first part of the document to keep the LLM call fast.
        snippet = text[:1500].strip()

        prompt = f"""You are an administrative document parser.

Extract the following fields from the document text below.
Respond with ONLY these lines, nothing else:

TITLE: <document title or main subject>
DOCUMENT_NUMBER: <reference/file number, or NONE>
DATE: <issue date, or NONE>
DEPARTMENT: <issuing department/section, or NONE>
CATEGORY: <one of: Circular, Office Order, Notification, Notice, Guidelines, Policy, Regulation, Other>

Document text:
{snippet}
"""

        print("[Metadata] Calling LLM for metadata extraction...")
        response = llm.invoke(prompt)

        # Parse the structured response
        meta = DocumentMetadata()
        for line in response.strip().split("\n"):
            line = line.strip()
            if line.startswith("TITLE:"):
                val = line.replace("TITLE:", "").strip()
                if val.upper() != "NONE" and val:
                    meta.title = val
            elif line.startswith("DOCUMENT_NUMBER:"):
                val = line.replace("DOCUMENT_NUMBER:", "").strip()
                if val.upper() != "NONE" and val:
                    meta.document_number = val
            elif line.startswith("DATE:"):
                val = line.replace("DATE:", "").strip()
                if val.upper() != "NONE" and val:
                    meta.date = val
            elif line.startswith("DEPARTMENT:"):
                val = line.replace("DEPARTMENT:", "").strip()
                if val.upper() != "NONE" and val:
                    meta.department = val
            elif line.startswith("CATEGORY:"):
                val = line.replace("CATEGORY:", "").strip()
                if val.upper() != "NONE" and val:
                    meta.category = val

        print(f"[Metadata] LLM extracted: title='{meta.title}', category='{meta.category}'")
        return meta

    except Exception as e:
        print(f"[Metadata] LLM extraction failed: {e}. Using filename as fallback.")
        # Last resort: use the filename as the title
        return DocumentMetadata(title=Path(filename).stem.replace("_", " ").replace("-", " ").title())


def extract_metadata(text: str, filename: str) -> DocumentMetadata:
    """
    Main metadata extraction function.

    Tries Regex first (fast, no LLM). Falls back to LLM only if the
    title — the most important field — could not be found.

    Args:
        text     : Full extracted text from the PDF.
        filename : PDF filename (used as title fallback of last resort).

    Returns:
        DocumentMetadata object with all available fields populated.
    """
    from pathlib import Path

    print(f"[Metadata] Extracting metadata for '{filename}'...")

    # Step 1: Try regex
    meta = extract_metadata_with_regex(text)

    # Step 2: If title is missing, escalate to LLM
    if not meta.title:
        print("[Metadata] Regex couldn't find title — trying LLM...")
        llm_meta = extract_metadata_with_llm(text, filename)
        # Merge: use LLM values for fields regex didn't find
        meta.title           = llm_meta.title           or Path(filename).stem
        meta.document_number = meta.document_number     or llm_meta.document_number
        meta.date            = meta.date                or llm_meta.date
        meta.department      = meta.department          or llm_meta.department
        meta.category        = meta.category            or llm_meta.category
    else:
        print(f"[Metadata] Regex found title: '{meta.title}'")

    # Final fallback: title is the filename
    if not meta.title:
        meta.title = Path(filename).stem.replace("_", " ").replace("-", " ").title()

    return meta
