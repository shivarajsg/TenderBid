import io
import uuid
import pytest
from pathlib import Path

from app.services.storage_service import (
    FileSizeLimitExceededError,
    InvalidFileTypeError,
    LocalStorageService,
    PDF_MAGIC_BYTES,
    PathTraversalError,
)


@pytest.fixture
def storage(tmp_path):
    """Fixture providing an isolated LocalStorageService using a temporary directory."""
    return LocalStorageService(base_dir=str(tmp_path))


@pytest.mark.asyncio
async def test_save_valid_pdf_stream(storage, tmp_path):
    """Verify that a valid PDF stream is atomically saved, hashed, and measured."""
    content = PDF_MAGIC_BYTES + b"1.7\nSample tender PDF content for testing."
    file_obj = io.BytesIO(content)

    tender_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    rel_path = f"tenders/{tender_id}/{doc_id}.pdf"

    saved_rel_path, size_bytes, sha256_hash = await storage.save_pdf_stream(
        file_obj=file_obj,
        target_relative_path=rel_path,
    )

    assert saved_rel_path == f"tenders/{tender_id}/{doc_id}.pdf"
    assert size_bytes == len(content)
    assert len(sha256_hash) == 64

    # Verify physical file existence
    abs_path = storage.get_file_path(saved_rel_path)
    assert abs_path.is_file()
    assert abs_path.read_bytes() == content


@pytest.mark.asyncio
async def test_reject_invalid_magic_bytes(storage):
    """Verify that files lacking %PDF- magic bytes are rejected without persisting."""
    invalid_content = b"PK\x03\x04This is a ZIP or docx file disguised as a PDF."
    file_obj = io.BytesIO(invalid_content)

    rel_path = f"tenders/{uuid.uuid4()}/{uuid.uuid4()}.pdf"
    with pytest.raises(InvalidFileTypeError) as exc_info:
        await storage.save_pdf_stream(file_obj=file_obj, target_relative_path=rel_path)

    assert "magic bytes" in str(exc_info.value).lower()
    # Confirm no orphan file left
    assert not (storage.base_dir / rel_path).exists()


@pytest.mark.asyncio
async def test_reject_oversized_file(storage):
    """Verify that files exceeding the byte limit are aborted and partial temp files cleaned up."""
    # 500 KB limit for this test
    limit = 500 * 1024
    oversized = PDF_MAGIC_BYTES + (b"A" * (limit + 100))
    file_obj = io.BytesIO(oversized)

    rel_path = f"tenders/{uuid.uuid4()}/{uuid.uuid4()}.pdf"
    with pytest.raises(FileSizeLimitExceededError):
        await storage.save_pdf_stream(
            file_obj=file_obj,
            target_relative_path=rel_path,
            max_size_bytes=limit,
        )

    assert not (storage.base_dir / rel_path).exists()


def test_path_traversal_detection(storage):
    """Verify that path traversal attempts outside the upload sandbox are blocked."""
    malicious_paths = [
        "../../etc/passwd",
        r"..\..\Windows\System32\cmd.exe",
        "tenders/../../../secret.txt",
    ]

    for p in malicious_paths:
        with pytest.raises(PathTraversalError):
            storage._resolve_safe_path(p)


def test_delete_file(storage):
    """Verify safe deletion of stored files."""
    test_file = storage.base_dir / "tenders" / "test.txt"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text("sample")

    assert storage.delete_file("tenders/test.txt") is True
    assert not test_file.exists()
    assert storage.delete_file("tenders/nonexistent.txt") is False
