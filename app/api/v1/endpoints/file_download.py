"""
File download endpoint

Generates downloadable document files (TXT, DOCX, PDF, XLSX) from
original, translation, or proofreading text data stored in PostgreSQL.

Endpoint                          SQL Function
--------------------------------  ------------------------------------------
POST /                            au_get_file_original()
                                  au_get_file_translation_for_jsonb()
                                  au_get_file_proofreading_for_jsonb()

Request Body (FileDownloadRequest):
    - file_id: UUID (required -- used by existing SQL functions)
    - Exactly one of: original_id, translation_id, proofreading_id
    - format: "txt" | "docx" | "pdf" | "xlsx"
    - include_numbers: bool (prefix each segment with [sid])
    - column_title: str (document heading / sheet title)
    - version: "original" | "latest"
        - "original" = base column only (e.g., translated_text)
        - "latest"   = merge base + modified overlay (e.g., translated_text + translated_text_modified)

Source Table Mapping:
    ID provided        SQL Function                                             Base column          Modified column
    -----------------  -------------------------------------------------------  -------------------  ---------------------------
    original_id        au_get_file_original(:file_id, :original_id)             original_text        original_text_modified
    translation_id     au_get_file_translation_for_jsonb(:file_id, :id)         translated_text      translated_text_modified
    proofreading_id    au_get_file_proofreading_for_jsonb(:file_id, :id)        proofreaded_text     proofreaded_text_modified (planned)

See: scripts/schema-functions/schema-public.file.original.sql
     scripts/schema-functions/schema-public.file.translation.sql
     scripts/schema-functions/schema-public.file.proofreading.sql
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logger import get_logger
from app.models.file_download import FileDownloadRequest
from app.services.file_download_generator import (
    FILE_EXTENSIONS,
    MIME_TYPES,
    generate_docx,
    generate_pdf,
    generate_txt,
    generate_xlsx,
)

logger = get_logger(__name__, logging.INFO)

router: APIRouter = APIRouter()


def merge_segments(base_segments: list[dict[str, Any]], modified_segments: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """
    Merge base segments with modified overlay.

    The modified column stores only the segments that were changed by the user
    (sparse overlay). This function starts with the full base segment list and
    overrides matching sid entries from the modified list.

    Args:
        base_segments: Full list of segments from the base column
        modified_segments: Sparse list of changed segments from the modified column (may be None)

    Returns:
        Merged segment list with modifications applied
    """
    if not modified_segments:
        return base_segments

    # Build a lookup map from the modified segments for O(1) access
    modified_map: dict[int, str] = {s["sid"]: s["text"] for s in modified_segments}

    return [
        {"sid": s["sid"], "text": modified_map.get(s["sid"], s["text"])}
        for s in base_segments
    ]


@router.post(
    "/",
    status_code=status.HTTP_200_OK,
    responses={
        400: {"description": "Invalid request (no valid source ID or missing text data)"},
        404: {"description": "Record not found"},
        500: {"description": "Internal server error"},
    },
)
async def download_file(
    download_data: FileDownloadRequest,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """
    Generate and return a downloadable document file.

    Fetches text data from the appropriate table (original, translation,
    or proofreading) using existing SQL functions, optionally merges
    base + modified overlay, and generates a file in the requested format.
    """

    try:
        # ------------------------------------------------------------------
        # 1. Determine which source ID was provided and call the
        #    corresponding existing SQL function to fetch text data
        # ------------------------------------------------------------------
        if download_data.original_id is not None:
            # au_get_file_original(p_file_id, p_original_id)
            # See: scripts/schema-functions/schema-public.file.original.sql
            result = await db.execute(
                text("""
                    SELECT original_text, original_text_modified
                    FROM au_get_file_original(:file_id, :original_id)
                """),
                {
                    "file_id": download_data.file_id,
                    "original_id": download_data.original_id,
                },
            )
            record_id = download_data.original_id
            base_column = "original_text"
            modified_column = "original_text_modified"
            source_label = "original"

        elif download_data.translation_id is not None:
            # au_get_file_translation_for_jsonb(p_file_id, p_translation_id)
            # See: scripts/schema-functions/schema-public.file.translation.sql
            result = await db.execute(
                text("""
                    SELECT translated_text, translated_text_modified
                    FROM au_get_file_translation_for_jsonb(:file_id, :translation_id)
                """),
                {
                    "file_id": download_data.file_id,
                    "translation_id": download_data.translation_id,
                },
            )
            record_id = download_data.translation_id
            base_column = "translated_text"
            modified_column = "translated_text_modified"
            source_label = "translation"

        elif download_data.proofreading_id is not None:
            # au_get_file_proofreading_for_jsonb(p_file_id, p_proofreading_id)
            # See: scripts/schema-functions/schema-public.file.proofreading.sql
            # Note: proofreaded_text_modified column is planned but not yet added.
            # The function currently does not return it; when the column is added,
            # update the SELECT to include proofreaded_text_modified.
            result = await db.execute(
                text("""
                    SELECT proofreaded_text
                    FROM au_get_file_proofreading_for_jsonb(:file_id, :proofreading_id)
                """),
                {
                    "file_id": download_data.file_id,
                    "proofreading_id": download_data.proofreading_id,
                },
            )
            record_id = download_data.proofreading_id
            base_column = "proofreaded_text"
            modified_column = None
            source_label = "proofreading"

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid source ID provided",
            )

        # ------------------------------------------------------------------
        # 2. Fetch the row from the query result
        # ------------------------------------------------------------------
        row = result.fetchone()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File {source_label} not found: {record_id}",
            )

        # ------------------------------------------------------------------
        # 3. Extract JSONB data and parse segments
        # ------------------------------------------------------------------
        base_data: dict[str, Any] | None = getattr(row, base_column, None)
        modified_data: dict[str, Any] | None = getattr(row, modified_column, None) if modified_column else None

        if not base_data or "segments" not in base_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No text data found in {source_label} record: {record_id}",
            )

        base_segments: list[dict[str, Any]] = base_data["segments"]

        # ------------------------------------------------------------------
        # 4. Resolve segments based on version
        #    - "original": use base column only
        #    - "latest":   merge base + modified overlay (fallback to base if modified is NULL)
        # ------------------------------------------------------------------
        if download_data.version == "original":
            segments = base_segments
        else:
            modified_segments = modified_data.get("segments") if modified_data else None
            segments = merge_segments(base_segments, modified_segments)

        # ------------------------------------------------------------------
        # 5. Generate the file using the appropriate generator
        # ------------------------------------------------------------------
        fmt = download_data.format
        include_numbers = download_data.include_numbers
        column_title = download_data.column_title

        if fmt == "txt":
            file_bytes = generate_txt(segments, include_numbers)
        elif fmt == "docx":
            file_bytes = generate_docx(segments, include_numbers, column_title)
        elif fmt == "pdf":
            file_bytes = generate_pdf(segments, include_numbers, column_title)
        elif fmt == "xlsx":
            file_bytes = generate_xlsx(segments, include_numbers, column_title)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported format: {fmt}",
            )

        # ------------------------------------------------------------------
        # 6. Build the filename and return the file response
        # ------------------------------------------------------------------
        filename = f"{column_title}{FILE_EXTENSIONS[fmt]}"
        mime_type = MIME_TYPES[fmt]

        logger.info(
            f"File download generated: format={fmt}, source={source_label}, "
            f"record_id={record_id}, segments={len(segments)}, "
            f"version={download_data.version}, size={len(file_bytes)} bytes"
        )

        return Response(
            content=file_bytes,
            media_type=mime_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
            },
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to generate file download: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate file download.",
        )
