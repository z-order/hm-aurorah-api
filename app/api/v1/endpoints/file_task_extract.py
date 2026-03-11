"""
File text extraction background task

Handles async text extraction from binary file formats (DOCX, PPTX, XLSX,
HWPX, PDF, EPUB, RTF, Video) using BackgroundTasks + RSMQ streaming.

Flow:
1. Download binary file from CDN
2. Extract text using format-specific extractor
3. Convert extracted text to segments via analyze_raw_text_to_json
4. Update au_file_original with extracted original_text
5. Send completion via RSMQ
"""

import json
import logging
import uuid
from collections.abc import Callable

from sqlalchemy import text

from app.core.config import settings
from app.core.database import AsyncSessionMaker
from app.core.logger import get_logger
from app.core.rsmqueue import RedisStreamMessageQueue
from app.utils.utils_file_extract import (
    extract_text_from_docx,
    extract_text_from_epub,
    extract_text_from_hwpx,
    extract_text_from_pdf,
    extract_text_from_pptx,
    extract_text_from_rtf,
    extract_text_from_video,
    extract_text_from_xlsx,
)
from app.utils.utils_file_validate import FileCategory, validate_file_extension
from app.utils.utils_http import read_binary_file_from_url
from app.utils.utils_text import analyze_raw_text_to_json

from .file_task_helpers import update_file_node_status

logger = get_logger(__name__, logging.DEBUG)

_EXTRACTORS: dict[FileCategory, Callable[[bytes], str]] = {
    FileCategory.DOCX: extract_text_from_docx,
    FileCategory.PPTX: extract_text_from_pptx,
    FileCategory.XLSX: extract_text_from_xlsx,
    FileCategory.HWPX: extract_text_from_hwpx,
    FileCategory.PDF: extract_text_from_pdf,
    FileCategory.EPUB: extract_text_from_epub,
    FileCategory.RTF: extract_text_from_rtf,
}


# =============================================================================
# MAIN BACKGROUND TASK
# =============================================================================


async def bg_atask_extract_file_text(
    rsmq_channel_id: str,
    file_id: uuid.UUID,
    original_id: uuid.UUID,
    file_url: str,
    file_ext: str,
    file_content: bytes | None = None,
) -> None:
    """
    Async background task for extracting text from a binary file.

    Args:
        rsmq_channel_id: Redis Stream MQ channel ID for progress streaming
        file_id: The file node ID in au_file_nodes (for status updates)
        original_id: The original record ID in au_file_original
        file_url: CDN URL of the file to extract text from
        file_ext: File extension (e.g. ".pdf", ".docx")
        file_content: Optional pre-downloaded file bytes (reused from validation for ZIP formats)
    """
    try:
        mq = RedisStreamMessageQueue(
            ttl_seconds=settings.REDIS_STREAM_MQ_TTL_SECONDS,
            maxlen=settings.REDIS_STREAM_MQ_MAXLEN,
        )

        # Step 1: Determine file category
        category = validate_file_extension(file_ext)

        # Step 2: Use pre-downloaded content or download from URL
        if file_content is not None:
            file_bytes = file_content
            logger.info(f"Reusing pre-downloaded file: {len(file_bytes)} bytes, ext={file_ext}")
        else:
            await mq.send(rsmq_channel_id, {"type": "progress", "message": "Downloading file..."})
            file_bytes = await read_binary_file_from_url(file_url)
            logger.info(f"Downloaded file: {len(file_bytes)} bytes, ext={file_ext}")

        # Step 3: Extract text
        await mq.send(rsmq_channel_id, {"type": "progress", "message": f"Extracting text from {file_ext} file..."})

        if category == FileCategory.VIDEO:
            raw_text = extract_text_from_video(file_url)
        else:
            extractor = _EXTRACTORS.get(category)
            if extractor is None:
                raise ValueError(f"No extractor for category: {category}")
            raw_text = extractor(file_bytes)

        logger.info(f"Extracted text: {len(raw_text)} chars from {file_ext}")

        # Step 4: Convert to segments
        await mq.send(rsmq_channel_id, {"type": "progress", "message": "Processing text segments..."})
        original_text = analyze_raw_text_to_json(raw_text)
        segment_count = len(original_text.get("segments", []))
        logger.info(f"Segmented into {segment_count} segments")

        # Step 5: Update database
        await _update_file_original(original_id, original_text)
        logger.info(f"Updated au_file_original: original_id={original_id}")

        # Step 6: Send completion
        await mq.send(rsmq_channel_id, {"type": "done"})
        logger.info(f"Text extraction completed: original_id={original_id}, segments={segment_count}")

    except NotImplementedError as e:
        logger.error(f"Text extraction not implemented: {str(e)}")
        await update_file_node_status(file_id, "failed", str(e))
        try:
            error_mq = RedisStreamMessageQueue(
                ttl_seconds=settings.REDIS_STREAM_MQ_TTL_SECONDS,
                maxlen=settings.REDIS_STREAM_MQ_MAXLEN,
            )
            await error_mq.send(rsmq_channel_id, {"type": "error", "message": str(e)})
        except Exception:
            pass

    except ValueError as e:
        logger.error(f"Text extraction validation error: {str(e)}")
        await update_file_node_status(file_id, "failed", str(e))
        try:
            error_mq = RedisStreamMessageQueue(
                ttl_seconds=settings.REDIS_STREAM_MQ_TTL_SECONDS,
                maxlen=settings.REDIS_STREAM_MQ_MAXLEN,
            )
            await error_mq.send(rsmq_channel_id, {"type": "error", "message": str(e)})
        except Exception:
            pass

    except Exception as e:
        error_type = type(e).__name__
        error_message = f"Text extraction failed ({error_type}). Check server logs."
        logger.error(f"Text extraction failed: {str(e)}", exc_info=True)
        await update_file_node_status(file_id, "failed", error_message)
        try:
            error_mq = RedisStreamMessageQueue(
                ttl_seconds=settings.REDIS_STREAM_MQ_TTL_SECONDS,
                maxlen=settings.REDIS_STREAM_MQ_MAXLEN,
            )
            await error_mq.send(rsmq_channel_id, {"type": "error", "message": error_message})
        except Exception:
            pass


# =============================================================================
# DATABASE HELPER
# =============================================================================


async def _update_file_original(
    original_id: uuid.UUID,
    original_text: dict[str, list[dict[str, str | int]]],
) -> None:
    """Update au_file_original with extracted text using existing SQL function."""
    async with AsyncSessionMaker() as db:
        result = await db.execute(
            text("""
                SELECT status, message
                FROM au_update_file_original(:original_id, :original_text, NULL)
            """),
            {
                "original_id": original_id,
                "original_text": json.dumps(original_text),
            },
        )
        row = result.fetchone()
        await db.commit()

        if row and row.status != 200:
            logger.warning(f"Update file original warning: {row.message}")
