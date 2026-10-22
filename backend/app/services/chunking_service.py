import hashlib
import logging
import uuid
from dataclasses import dataclass
from typing import List, Optional

from app.core.config import get_settings
from app.services.extraction_service import PageExtractionResult

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class DocumentChunk:
    """A bounded segment of document text with complete provenance metadata."""
    chunk_id: str
    text: str
    metadata: dict


class RecursiveCharacterChunker:
    """Splits text using a recursive character hierarchy while preserving provenance metadata."""

    def __init__(
        self,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        separators: Optional[List[str]] = None,
    ):
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP
        self.separators = separators or ["\n\n", "\n", ". ", " ", ""]

    def _split_text_recursive(self, text: str, separators: List[str]) -> List[str]:
        """Split text recursively by separators until pieces fit chunk_size."""
        final_chunks: List[str] = []
        separator = separators[-1]
        new_separators: List[str] = []

        for i, sep in enumerate(separators):
            if sep == "":
                separator = ""
                break
            if sep in text:
                separator = sep
                new_separators = separators[i + 1 :]
                break

        splits = text.split(separator) if separator != "" else list(text)

        good_splits: List[str] = []
        for s in splits:
            if not s:
                continue
            if len(s) < self.chunk_size:
                good_splits.append(s)
            else:
                if new_separators:
                    sub_splits = self._split_text_recursive(s, new_separators)
                    good_splits.extend(sub_splits)
                else:
                    good_splits.append(s[: self.chunk_size])

        # Merge splits up to chunk_size with chunk_overlap
        current_chunk: List[str] = []
        current_length = 0

        for piece in good_splits:
            piece_len = len(piece) + (len(separator) if current_chunk else 0)
            if current_length + piece_len <= self.chunk_size:
                current_chunk.append(piece)
                current_length += piece_len
            else:
                if current_chunk:
                    merged = separator.join(current_chunk).strip()
                    if merged:
                        final_chunks.append(merged)
                    # Handle overlap: retain pieces from end of current_chunk
                    overlap_chunk: List[str] = []
                    overlap_len = 0
                    for op in reversed(current_chunk):
                        if overlap_len + len(op) <= self.chunk_overlap:
                            overlap_chunk.insert(0, op)
                            overlap_len += len(op) + len(separator)
                        else:
                            break
                    current_chunk = overlap_chunk
                    current_length = overlap_len
                current_chunk.append(piece)
                current_length += len(piece)

        if current_chunk:
            merged = separator.join(current_chunk).strip()
            if merged:
                final_chunks.append(merged)

        return final_chunks

    def chunk_page(
        self,
        page: PageExtractionResult,
        tender_id: uuid.UUID,
        document_id: uuid.UUID,
        source_filename: str,
        start_chunk_index: int = 0,
    ) -> List[DocumentChunk]:
        """Chunk a single extracted page, retaining page provenance."""
        if not page.text.strip():
            return []

        raw_pieces = self._split_text_recursive(page.text, self.separators)
        chunks: List[DocumentChunk] = []

        char_cursor = 0
        for i, piece in enumerate(raw_pieces):
            clean_piece = piece.strip()
            if not clean_piece:
                continue

            chunk_idx = start_chunk_index + i
            chunk_hash = hashlib.sha256(clean_piece.encode("utf-8")).hexdigest()
            char_start = char_cursor
            char_end = char_cursor + len(clean_piece)
            char_cursor = char_end

            metadata = {
                "tender_id": str(tender_id),
                "document_id": str(document_id),
                "source_filename": source_filename,
                "page_number": page.page_number,
                "chunk_index": chunk_idx,
                "char_start": char_start,
                "char_end": char_end,
                "sha256_hash": chunk_hash,
                "extraction_method": page.extraction_method,
            }

            chunk_id = f"{document_id}_{chunk_idx}"
            chunks.append(DocumentChunk(chunk_id=chunk_id, text=clean_piece, metadata=metadata))

        return chunks

    def chunk_document_pages(
        self,
        pages: List[PageExtractionResult],
        tender_id: uuid.UUID,
        document_id: uuid.UUID,
        source_filename: str,
    ) -> List[DocumentChunk]:
        """Chunk all pages of a document sequentially, ensuring globally unique chunk indices."""
        all_chunks: List[DocumentChunk] = []
        global_idx = 0

        for page in pages:
            page_chunks = self.chunk_page(
                page=page,
                tender_id=tender_id,
                document_id=document_id,
                source_filename=source_filename,
                start_chunk_index=global_idx,
            )
            all_chunks.extend(page_chunks)
            global_idx += len(page_chunks)

        return all_chunks


_chunker = RecursiveCharacterChunker()


def get_chunking_service() -> RecursiveCharacterChunker:
    """Dependency provider for RecursiveCharacterChunker."""
    return _chunker
