"""
File edit history endpoints

Endpoint                    SQL Function
--------------------------  ------------------
POST /                      au_create_file_edit_history()
GET /{file_id}              au_get_file_edit_history()

SQL Function                    Status Codes
------------------------------  --------------------------
au_create_file_edit_history     200(OK)
au_get_file_edit_history        (no status, returns rows)

See: scripts/schema-functions/schema-public.file.edit-history.sql
"""

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logger import get_logger
from app.models.file_edit_history import FileEditHistoryCreate, FileEditHistoryCreateResponse, FileEditHistoryRead

logger = get_logger(__name__, logging.INFO)

router: APIRouter = APIRouter()


@router.post(
    "/",
    response_model=FileEditHistoryCreateResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        500: {"description": "Internal server error"},
    },
)
async def create_file_edit_history(
    history_data: FileEditHistoryCreate,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Create new file edit history
    """

    try:
        result = await db.execute(
            text("""
                SELECT status, message, history_id
                FROM au_create_file_edit_history(
                    :file_id,
                    :target_type,
                    :target_id,
                    :marker_number,
                    :editor_id,
                    :text_before,
                    :text_after,
                    :comments
                )
            """),
            {
                "file_id": history_data.file_id,
                "target_type": history_data.target_type,
                "target_id": history_data.target_id,
                "marker_number": history_data.marker_number,
                "editor_id": history_data.editor_id,
                "text_before": history_data.text_before,
                "text_after": history_data.text_after,
                "comments": history_data.comments,
            },
        )
        row = result.fetchone()
        await db.commit()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create file edit history",
            )

        return {"history_id": row.history_id}

    except HTTPException:
        await db.rollback()
        raise

    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create file edit history: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create file edit history.",
        )


@router.get(
    "/{file_id}",
    response_model=list[FileEditHistoryRead],
    responses={
        500: {"description": "Internal server error"},
    },
)
async def get_file_edit_history(
    file_id: uuid.UUID,
    target_type: str | None = Query(
        default=None, description="Target type filter (original, translation, proofreading)"
    ),
    target_id: uuid.UUID | None = Query(default=None, description="Target ID filter"),
    marker_number: int | None = Query(default=None, description="Marker number filter"),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """
    Retrieve file edit history

    Filters:
    - target_type: Filter by target type (original, translation, proofreading)
    - target_id: Filter by target ID
    - marker_number: Filter by marker number
    """

    try:
        result = await db.execute(
            text("""
                SELECT history_id, file_id, target_type, target_id, marker_number,
                       editor_id, text_before, text_after, comments, created_at
                FROM au_get_file_edit_history(:file_id, :target_type, :target_id, :marker_number)
            """),
            {
                "file_id": file_id,
                "target_type": target_type,
                "target_id": target_id,
                "marker_number": marker_number,
            },
        )
        rows = result.fetchall()

        return [
            {
                "history_id": row.history_id,
                "file_id": row.file_id,
                "target_type": row.target_type,
                "target_id": row.target_id,
                "marker_number": row.marker_number,
                "editor_id": row.editor_id,
                "text_before": row.text_before,
                "text_after": row.text_after,
                "comments": row.comments,
                "created_at": row.created_at,
            }
            for row in rows
        ]

    except Exception as e:
        logger.error(f"Failed to retrieve file edit history: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve file edit history.",
        )
