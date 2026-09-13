"""
Unit tests for utils/pdf_extractor.py.
Validates extraction accuracy, boundary conditions, edge cases, and scan heuristics.
"""

import io
import pytest
import pymupdf as fitz
from utils.pdf_extractor import extract_text_from_pdf, PDFExtractionResult, MAX_PAGES, MAX_CHARS


def test_valid_pdf_extraction(sample_pdf_bytes):
    """Verifies that text is successfully extracted from a valid lecture PDF."""
    result = extract_text_from_pdf(sample_pdf_bytes)
    assert isinstance(result, PDFExtractionResult)
    assert not result.is_empty
    assert result.page_count == 1
    assert "CPU Scheduling Algorithms" in result.text
    assert "FCFS" in result.text
    assert "Round Robin" in result.text


def test_corrupted_pdf_bytes():
    """Verifies that corrupted bytes raise a clear ValueError."""
    corrupted_data = b"NOT_A_VALID_PDF_HEADER_OR_BODY_12345"
    with pytest.raises(ValueError, match="Could not open PDF file"):
        extract_text_from_pdf(corrupted_data)


def test_empty_or_scanned_pdf(empty_pdf_bytes):
    """Verifies that an empty/scanned PDF triggers the scan warning and is_empty flag."""
    result = extract_text_from_pdf(empty_pdf_bytes)
    assert result.is_empty
    assert result.text == ""
    assert result.warning is not None
    assert "scanned images" in result.warning.lower()


def test_large_character_truncation():
    """Verifies that PDFs exceeding MAX_CHARS are safely truncated with an explanatory warning."""
    doc = fitz.open()
    chunk = ("Operating systems manage memory, processes, storage, and devices.\n" * 35)
    for _ in range(30):
        page = doc.new_page()
        page.insert_text((40, 40), chunk, fontsize=8)
    
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    
    result = extract_text_from_pdf(buf.getvalue())
    assert len(result.text) <= MAX_CHARS
    assert result.warning is not None
    assert "trimmed" in result.warning.lower()


def test_max_pages_limit_handling():
    """Verifies that PDFs exceeding MAX_PAGES cap processing at MAX_PAGES."""
    doc = fitz.open()
    for i in range(MAX_PAGES + 5):
        page = doc.new_page()
        page.insert_text((50, 50), f"Slide {i + 1}: Technical Content for Exam Revision", fontsize=10)
    
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()

    result = extract_text_from_pdf(buf.getvalue())
    assert result.page_count == MAX_PAGES + 5
    assert result.warning is not None
    assert f"first {MAX_PAGES} pages" in result.warning
