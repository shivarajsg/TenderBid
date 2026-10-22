from pathlib import Path
from unittest.mock import MagicMock
import pytest
import pymupdf

from app.services.extraction_service import (
    DocumentExtractionService,
    LOW_DENSITY_CHAR_THRESHOLD,
)
from app.services.ocr_service import OCRService


def create_sample_pdf(file_path: Path, page1_text: str, page2_text: str) -> None:
    """Helper to generate a real multi-page PDF using PyMuPDF for deterministic test runs."""
    doc = pymupdf.open()
    
    # Page 1
    page1 = doc.new_page()
    page1.insert_text((50, 50), page1_text, fontsize=12)
    
    # Page 2
    page2 = doc.new_page()
    page2.insert_text((50, 50), page2_text, fontsize=12)
    
    doc.save(str(file_path))
    doc.close()


def test_pymupdf_page_by_page_text_extraction(tmp_path):
    """Verify PyMuPDF extracts text page by page with 1-based physical page numbers."""
    pdf_path = tmp_path / "test_notice.pdf"
    
    # Text longer than LOW_DENSITY_CHAR_THRESHOLD (100)
    p1 = "Notice Inviting Tender (NIT) - Page 1. The National Thermal Power Corporation invites bids for the supply of high-voltage electrical transformers in accordance with technical specifications detailed herein."
    p2 = "Eligibility and Financial Criteria - Page 2. The bidder must have an average annual turnover of not less than INR 50 Crores over the last three audited financial years, and must hold ISO 9001:2015 certification."
    
    create_sample_pdf(pdf_path, p1, p2)

    service = DocumentExtractionService()
    result = service.extract_document(pdf_path)

    assert result.total_pages == 2
    assert len(result.pages) == 2

    # Check 1-based page numbering
    assert result.pages[0].page_number == 1
    assert "Notice Inviting Tender" in result.pages[0].text
    assert result.pages[0].extraction_method == "pymupdf_direct"
    assert result.pages[0].ocr_applied is False
    assert result.pages[0].char_count > 100

    assert result.pages[1].page_number == 2
    assert "Eligibility and Financial Criteria" in result.pages[1].text
    assert result.pages[1].extraction_method == "pymupdf_direct"
    assert result.pages[1].ocr_applied is False

    meta = result.to_metadata_dict()
    assert meta["total_pages"] == 2
    assert len(meta["pages"]) == 2
    assert meta["pages"][0]["page_number"] == 1


def test_low_density_page_ocr_fallback_degraded(tmp_path):
    """Verify that a text-poor page gracefully degrades to 'pymupdf_degraded' when OCR is unavailable."""
    pdf_path = tmp_path / "scanned_sample.pdf"
    p1 = "Scanned Page Heading"  # Short text, < 100 chars
    p2 = "Page 2 with sufficient text length: The contractor shall execute and complete the entire scope of work within the prescribed timeline of six calendar months from letter of award."
    
    create_sample_pdf(pdf_path, p1, p2)

    # Mock OCR service to simulate unavailable Tesseract binary on host
    mock_ocr = MagicMock(spec=OCRService)
    mock_ocr.is_available.return_value = False

    service = DocumentExtractionService(ocr_service=mock_ocr)
    result = service.extract_document(pdf_path)

    assert result.total_pages == 2
    assert result.pages[0].page_number == 1
    assert result.pages[0].char_count < LOW_DENSITY_CHAR_THRESHOLD
    assert result.pages[0].extraction_method == "pymupdf_degraded"
    assert result.pages[0].ocr_applied is False
    assert result.degraded_pages_count == 1

    # Page 2 should still be pymupdf_direct
    assert result.pages[1].extraction_method == "pymupdf_direct"


def test_ocr_fallback_applied_when_available(tmp_path):
    """Verify that when OCR is available, text-poor pages are processed via Tesseract OCR."""
    pdf_path = tmp_path / "scanned_with_ocr.pdf"
    p1 = "Short"  # Low density
    p2 = "Page 2 normal text that exceeds one hundred characters easily because it describes extensive procurement parameters for industrial equipment."
    
    create_sample_pdf(pdf_path, p1, p2)

    mock_ocr = MagicMock(spec=OCRService)
    mock_ocr.is_available.return_value = True
    mock_ocr.extract_text_from_pixmap_bytes.return_value = (
        "OCR Extracted Content: Ministry of Heavy Industries - Technical Bid Document Page 1 Scanned Seal."
    )

    service = DocumentExtractionService(ocr_service=mock_ocr)
    result = service.extract_document(pdf_path)

    assert result.pages[0].page_number == 1
    assert result.pages[0].ocr_applied is True
    assert result.pages[0].extraction_method == "tesseract_ocr"
    assert "OCR Extracted Content" in result.pages[0].text
    assert result.ocr_pages_count == 1
