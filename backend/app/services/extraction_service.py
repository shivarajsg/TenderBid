import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
import pymupdf  # PyMuPDF v2.0+

from app.services.ocr_service import OCRService, get_ocr_service

logger = logging.getLogger(__name__)

# Minimum character count to qualify as a valid text-dense PDF page
LOW_DENSITY_CHAR_THRESHOLD = 100


@dataclass
class PageExtractionResult:
    """Structured extraction outcome for a single physical PDF page."""
    page_number: int  # 1-based index
    text: str
    char_count: int
    ocr_applied: bool
    extraction_method: str  # "pymupdf_direct", "tesseract_ocr", "pymupdf_degraded"
    density_score: float  # Non-whitespace chars / total chars


@dataclass
class DocumentExtractionResult:
    """Full extraction outcome for a document."""
    total_pages: int
    total_characters: int
    pages: List[PageExtractionResult] = field(default_factory=list)
    ocr_pages_count: int = 0
    degraded_pages_count: int = 0

    def to_metadata_dict(self) -> dict:
        """Serialize extraction metadata for storage in the relational database."""
        return {
            "total_pages": self.total_pages,
            "total_characters": self.total_characters,
            "ocr_pages_count": self.ocr_pages_count,
            "degraded_pages_count": self.degraded_pages_count,
            "pages": [
                {
                    "page_number": p.page_number,
                    "char_count": p.char_count,
                    "ocr_applied": p.ocr_applied,
                    "extraction_method": p.extraction_method,
                    "density_score": round(p.density_score, 4),
                }
                for p in self.pages
            ],
        }


class DocumentExtractionService:
    """Extracts text page-by-page from PDFs with automatic OCR fallback for scanned pages."""

    def __init__(self, ocr_service: Optional[OCRService] = None):
        self.ocr_service = ocr_service or get_ocr_service()

    def extract_document(self, file_path: Path) -> DocumentExtractionResult:
        """
        Open the PDF using PyMuPDF and extract text page by page.
        Applies OCR fallback if text density is below threshold.
        """
        if not file_path.is_file():
            raise FileNotFoundError(f"PDF document not found at: {file_path}")

        doc = pymupdf.open(str(file_path))
        total_pages = len(doc)
        pages_result: List[PageExtractionResult] = []
        total_characters = 0
        ocr_count = 0
        degraded_count = 0

        try:
            for page_idx in range(total_pages):
                page_number = page_idx + 1  # 1-based page numbering
                page = doc[page_idx]

                # PyMuPDF direct text extraction
                extracted_text = page.get_text("text").strip()
                char_count = len(extracted_text)

                # Check if page is low density / scanned image
                if char_count < LOW_DENSITY_CHAR_THRESHOLD:
                    if self.ocr_service.is_available():
                        try:
                            # Render page to high-res image (200 DPI) for OCR
                            pix = page.get_pixmap(dpi=200)
                            ocr_text = self.ocr_service.extract_text_from_pixmap_bytes(pix.tobytes("png"))
                            if len(ocr_text) > char_count:
                                extracted_text = ocr_text
                                char_count = len(extracted_text)
                                ocr_applied = True
                                method = "tesseract_ocr"
                                ocr_count += 1
                            else:
                                ocr_applied = False
                                method = "pymupdf_direct"
                        except Exception as e:
                            logger.warning(f"OCR failed for page {page_number}: {e}")
                            ocr_applied = False
                            method = "pymupdf_degraded"
                            degraded_count += 1
                    else:
                        ocr_applied = False
                        method = "pymupdf_degraded"
                        degraded_count += 1
                else:
                    ocr_applied = False
                    method = "pymupdf_direct"

                # Density score calculation
                non_ws = len("".join(extracted_text.split()))
                density_score = (non_ws / char_count) if char_count > 0 else 0.0

                page_res = PageExtractionResult(
                    page_number=page_number,
                    text=extracted_text,
                    char_count=char_count,
                    ocr_applied=ocr_applied,
                    extraction_method=method,
                    density_score=density_score,
                )
                pages_result.append(page_res)
                total_characters += char_count

            return DocumentExtractionResult(
                total_pages=total_pages,
                total_characters=total_characters,
                pages=pages_result,
                ocr_pages_count=ocr_count,
                degraded_pages_count=degraded_count,
            )

        finally:
            doc.close()


_extraction_service = DocumentExtractionService()


def get_extraction_service() -> DocumentExtractionService:
    """Dependency provider for DocumentExtractionService."""
    return _extraction_service
