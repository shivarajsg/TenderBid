import io
import logging
import shutil
from typing import Optional
from PIL import Image
import pytesseract

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class OCRAvailabilityError(Exception):
    """Raised when an OCR operation is requested but Tesseract binary is not installed or available."""
    pass


class OCRService:
    """Optical Character Recognition service wrapping Tesseract with graceful host detection."""

    def __init__(self, tesseract_cmd: Optional[str] = None):
        self.cmd = tesseract_cmd or settings.TESSERACT_CMD
        if self.cmd:
            pytesseract.pytesseract.tesseract_cmd = self.cmd
        self._is_available: Optional[bool] = None

    def is_available(self) -> bool:
        """Check if Tesseract binary is callable in the current execution environment."""
        if self._is_available is not None:
            return self._is_available

        # First check if explicit cmd exists or is in PATH
        if self.cmd and not shutil.which(self.cmd):
            self._is_available = False
            logger.warning(f"Configured Tesseract binary not found at '{self.cmd}'. OCR will operate in degraded mode.")
            return False

        try:
            version = pytesseract.get_tesseract_version()
            logger.info(f"Tesseract OCR host engine verified (version: {version})")
            self._is_available = True
        except Exception as e:
            logger.warning(f"Tesseract OCR binary not found or failed execution: {e}. Scanned page OCR will degrade gracefully.")
            self._is_available = False

        return self._is_available

    def extract_text_from_image(self, image: Image.Image, lang: str = "eng") -> str:
        """Run OCR on a PIL Image object."""
        if not self.is_available():
            raise OCRAvailabilityError("Tesseract OCR binary is not installed or accessible on this host system.")

        try:
            text = pytesseract.image_to_string(image, lang=lang)
            return text.strip()
        except Exception as e:
            logger.error(f"OCR execution failed: {e}")
            raise

    def extract_text_from_pixmap_bytes(self, image_bytes: bytes, lang: str = "eng") -> str:
        """Run OCR on raw image bytes (e.g. from PyMuPDF pixmap)."""
        image = Image.open(io.BytesIO(image_bytes))
        return self.extract_text_from_image(image, lang=lang)


_ocr_service = OCRService()


def get_ocr_service() -> OCRService:
    """Dependency provider for OCRService."""
    return _ocr_service
