"""
PDF text extraction utility.
Uses PyMuPDF (fitz) for robust, fast text extraction from lecture PDFs.
Detects scanned/image-only PDFs so the app can warn the user gracefully.
"""

try:
    import pymupdf as fitz
except ImportError:
    import fitz

# Hard cap to keep API calls fast and within token limits for a hackathon demo.
MAX_PAGES = 60
MAX_CHARS = 45000


class PDFExtractionResult:
    def __init__(self, text: str, page_count: int, warning: str | None = None):
        self.text = text
        self.page_count = page_count
        self.warning = warning
        self.is_empty = len(text.strip()) == 0


def extract_text_from_pdf(file_bytes: bytes) -> PDFExtractionResult:
    """
    Extracts text from an in-memory PDF file.

    Args:
        file_bytes: Raw bytes of the uploaded PDF.

    Returns:
        PDFExtractionResult with extracted text, page count, and any warnings.
    """
    warning = None

    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as e:
        raise ValueError(f"Could not open PDF file. It may be corrupted. ({e})")

    page_count = doc.page_count

    if page_count == 0:
        doc.close()
        raise ValueError("The uploaded PDF has no pages.")

    if page_count > MAX_PAGES:
        warning = (
            f"This PDF has {page_count} pages. For speed and reliability, only the "
            f"first {MAX_PAGES} pages were processed."
        )

    pages_to_read = min(page_count, MAX_PAGES)
    text_chunks = []
    chars_with_text = 0

    for i in range(pages_to_read):
        page = doc.load_page(i)
        page_text = page.get_text("text")
        if page_text.strip():
            chars_with_text += len(page_text.strip())
        text_chunks.append(page_text)

    doc.close()

    full_text = "\n".join(text_chunks).strip()

    # Heuristic: very little extractable text relative to page count usually
    # means the PDF is scanned images without an OCR text layer.
    avg_chars_per_page = chars_with_text / pages_to_read if pages_to_read else 0
    if avg_chars_per_page < 20:
        scan_warning = (
            "This PDF appears to contain scanned images with little or no "
            "selectable text. Try uploading a text-based PDF, or run OCR on "
            "it first."
        )
        warning = f"{warning} {scan_warning}" if warning else scan_warning

    # Truncate to keep prompt size reasonable.
    if len(full_text) > MAX_CHARS:
        full_text = full_text[:MAX_CHARS]
        trunc_warning = (
            f"The extracted text was long, so it was trimmed to the first "
            f"{MAX_CHARS:,} characters for processing."
        )
        warning = f"{warning} {trunc_warning}" if warning else trunc_warning

    return PDFExtractionResult(text=full_text, page_count=page_count, warning=warning)
