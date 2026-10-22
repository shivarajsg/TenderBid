import hashlib
import os
import uuid
from pathlib import Path
from typing import BinaryIO, Optional, Tuple

from app.core.config import get_settings

settings = get_settings()

PDF_MAGIC_BYTES = b"%PDF-"


class StorageServiceError(Exception):
    """Base exception for file storage errors."""
    pass


class InvalidFileTypeError(StorageServiceError):
    """Raised when file content fails magic bytes or MIME inspection."""
    pass


class FileSizeLimitExceededError(StorageServiceError):
    """Raised when file exceeds the maximum allowed size in MB."""
    pass


class PathTraversalError(StorageServiceError):
    """Raised when a resolved file path attempts to escape the root upload sandbox."""
    pass


class LocalStorageService:
    """Secure, sandboxed filesystem storage manager for PDFs and documents."""

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = Path(base_dir or settings.UPLOAD_DIR).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_safe_path(self, relative_path: str) -> Path:
        """Resolve path and verify it stays strictly inside the configured UPLOAD_DIR sandbox."""
        # Normalize separators
        clean_rel = os.path.normpath(relative_path).lstrip(r"\/")
        target_path = (self.base_dir / clean_rel).resolve()

        try:
            target_path.relative_to(self.base_dir)
        except ValueError:
            raise PathTraversalError(f"Security violation: path traversal detected for '{relative_path}'")

        return target_path

    def get_tender_dir(self, tender_id: uuid.UUID) -> Path:
        """Return and create the sandboxed folder for a tender's attachments."""
        tender_dir = self._resolve_safe_path(f"tenders/{tender_id}")
        tender_dir.mkdir(parents=True, exist_ok=True)
        return tender_dir

    def get_company_dir(self, company_id: uuid.UUID) -> Path:
        """Return and create the sandboxed folder for a company's vault documents."""
        company_dir = self._resolve_safe_path(f"companies/{company_id}")
        company_dir.mkdir(parents=True, exist_ok=True)
        return company_dir

    async def save_pdf_stream(
        self,
        file_obj: BinaryIO,
        target_relative_path: str,
        max_size_bytes: Optional[int] = None,
    ) -> Tuple[str, int, str]:
        """
        Validates magic bytes, verifies size limit, and atomically writes the PDF to disk.
        Returns: (saved_relative_path, total_size_bytes, sha256_hash)
        """
        if max_size_bytes is None:
            max_size_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024

        target_path = self._resolve_safe_path(target_relative_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = target_path.with_suffix(f".tmp_{uuid.uuid4().hex}")

        hasher = hashlib.sha256()
        total_size = 0
        header_checked = False

        try:
            with open(temp_path, "wb") as f_out:
                while True:
                    chunk = file_obj.read(65536)
                    if not chunk:
                        break

                    if not header_checked:
                        if not chunk.startswith(PDF_MAGIC_BYTES):
                            raise InvalidFileTypeError(
                                "Invalid file signature: file does not start with %PDF- magic bytes"
                            )
                        header_checked = True

                    total_size += len(chunk)
                    if total_size > max_size_bytes:
                        raise FileSizeLimitExceededError(
                            f"File size exceeds maximum allowed limit of {settings.MAX_UPLOAD_SIZE_MB} MB"
                        )

                    hasher.update(chunk)
                    f_out.write(chunk)

            if not header_checked or total_size == 0:
                raise InvalidFileTypeError("File is empty or corrupted (missing %PDF- header)")

            # Atomic rename into final location
            if temp_path.exists():
                temp_path.replace(target_path)

            rel_path = str(target_path.relative_to(self.base_dir)).replace("\\", "/")
            return rel_path, total_size, hasher.hexdigest()

        except Exception:
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError:
                    pass
            raise

    def get_file_path(self, relative_path: str) -> Path:
        """Resolve a stored file path and verify existence."""
        target_path = self._resolve_safe_path(relative_path)
        if not target_path.is_file():
            raise FileNotFoundError(f"Stored file does not exist: {relative_path}")
        return target_path

    def delete_file(self, relative_path: str) -> bool:
        """Safely delete a stored file if it exists."""
        try:
            target_path = self._resolve_safe_path(relative_path)
            if target_path.is_file():
                target_path.unlink()
                return True
        except Exception:
            pass
        return False


_storage_service = LocalStorageService()


def get_storage_service() -> LocalStorageService:
    """Dependency provider returning singleton LocalStorageService."""
    return _storage_service
