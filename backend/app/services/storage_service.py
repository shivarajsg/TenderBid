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

    def __init__(self, base_dir: Optional[str] = None, downloads_dir: Optional[str] = None):
        self.base_dir = Path(base_dir or settings.UPLOAD_DIR).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)
        if downloads_dir:
            self.downloads_dir = Path(downloads_dir).resolve()
        else:
            raw_dl = getattr(settings, "TENDER_DOWNLOAD_DIR", "downloads")
            if Path(raw_dl).is_absolute():
                self.downloads_dir = Path(raw_dl).resolve()
            else:
                project_root = Path(__file__).resolve().parents[3]
                clean_name = raw_dl.replace("../", "").replace("..\\", "").strip("/\\")
                self.downloads_dir = (project_root / (clean_name or "downloads")).resolve()
        self.downloads_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_safe_path(self, relative_path: str) -> Path:
        """Resolve path and verify it stays strictly inside the configured UPLOAD_DIR or downloads sandbox."""
        # Normalize separators
        clean_rel = os.path.normpath(relative_path).lstrip(r"\/")

        # Check if targeting downloads directory explicitly
        if clean_rel.lower().startswith("downloads/") or clean_rel.lower().startswith("downloads\\"):
            sub_rel = clean_rel[10:].lstrip(r"\/")
            target_path = (self.downloads_dir / sub_rel).resolve()
            try:
                target_path.relative_to(self.downloads_dir)
            except ValueError:
                raise PathTraversalError(f"Security violation: path traversal detected for '{relative_path}'")
            return target_path

        target_path = (self.base_dir / clean_rel).resolve()

        try:
            target_path.relative_to(self.base_dir)
        except ValueError:
            # Check if it was meant to be relative to downloads_dir
            alt_path = (self.downloads_dir / clean_rel).resolve()
            try:
                alt_path.relative_to(self.downloads_dir)
                if alt_path.exists():
                    return alt_path
            except ValueError:
                pass
            raise PathTraversalError(f"Security violation: path traversal detected for '{relative_path}'")

        # Fallback: if not found in base_dir, but exists in downloads_dir, return that
        if not target_path.exists() and (self.downloads_dir / clean_rel).resolve().is_file():
            return (self.downloads_dir / clean_rel).resolve()

        return target_path

    def get_tender_download_dir(self, tender_dir_name: str) -> Path:
        """Return and create the tender-specific subfolder in downloads directory."""
        clean_dir = os.path.normpath(tender_dir_name).lstrip(r"\/")
        tender_dir = (self.downloads_dir / clean_dir).resolve()
        try:
            tender_dir.relative_to(self.downloads_dir)
        except ValueError:
            raise PathTraversalError(f"Security violation: invalid tender directory name '{tender_dir_name}'")
        tender_dir.mkdir(parents=True, exist_ok=True)
        return tender_dir

    async def save_tender_download_file(
        self,
        file_bytes: bytes,
        tender_dir_name: str,
        filename: str,
        max_size_bytes: Optional[int] = None,
        verify_pdf_header: bool = False,
    ) -> Tuple[str, Path, int, str]:
        """
        Atomically saves a downloaded tender PDF or attachment into the downloads/<tender_dir_name>/ folder.
        Returns: (rel_storage_path, absolute_file_path, total_size_bytes, sha256_hash)
        """
        if max_size_bytes is None:
            max_size_bytes = getattr(settings, "MAX_DOCUMENT_DOWNLOAD_BYTES", 50 * 1024 * 1024)

        if len(file_bytes) > max_size_bytes:
            raise FileSizeLimitExceededError(
                f"File size ({len(file_bytes)} bytes) exceeds limit ({max_size_bytes} bytes)"
            )

        if verify_pdf_header and not file_bytes.startswith(PDF_MAGIC_BYTES):
            raise InvalidFileTypeError("Invalid file signature: does not start with %PDF- header")

        tender_folder = self.get_tender_download_dir(tender_dir_name)
        clean_filename = os.path.normpath(filename).lstrip(r"\/")
        target_path = (tender_folder / clean_filename).resolve()

        try:
            target_path.relative_to(self.downloads_dir)
        except ValueError:
            raise PathTraversalError(f"Security violation: invalid filename '{filename}'")

        temp_path = target_path.with_suffix(f".tmp_{uuid.uuid4().hex}")
        hasher = hashlib.sha256(file_bytes)

        with open(temp_path, "wb") as f_out:
            f_out.write(file_bytes)

        if temp_path.exists():
            temp_path.replace(target_path)

        clean_tender_dir = os.path.normpath(tender_dir_name).replace("\\", "/").strip("/")
        clean_fn = clean_filename.replace("\\", "/").strip("/")
        rel_storage_path = f"downloads/{clean_tender_dir}/{clean_fn}"
        return rel_storage_path, target_path, len(file_bytes), hasher.hexdigest()

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
