"""
File checkpoint endpoints

Endpoint                    SQL Function
--------------------------  ------------------
POST /                      au_create_file_checkpoint()
GET /{file_id}              au_get_file_checkpoint()

SQL Function                  Status Codes
----------------------------  --------------------------
au_create_file_checkpoint     200(OK), 404(Not Found)
au_get_file_checkpoint        (no status, returns rows)

See: scripts/schema-functions/schema-public.file.checkpoint.sql
"""

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logger import get_logger
from app.models.file_checkpoint import FileCheckpointCreate, FileCheckpointCreateResponse, FileCheckpointRead

logger = get_logger(__name__, logging.INFO)

router: APIRouter = APIRouter()


@router.post(
    "/",
    response_model=FileCheckpointCreateResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        404: {"description": "File not found / Edit history not found"},
        500: {"description": "Internal server error"},
    },
)
async def create_file_checkpoint(
    checkpoint_data: FileCheckpointCreate,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Create new file checkpoint
    """

    try:
        result = await db.execute(
            text("""
                SELECT status, message, checkpoint_id
                FROM au_create_file_checkpoint(
                    :file_id,
                    :history_id,
                    :original_text_modified,
                    :translated_text_modified,
                    :proofreaded_text
                )
            """),
            {
                "file_id": checkpoint_data.file_id,
                "history_id": checkpoint_data.history_id,
                "original_text_modified": checkpoint_data.original_text_modified,
                "translated_text_modified": checkpoint_data.translated_text_modified,
                "proofreaded_text": checkpoint_data.proofreaded_text,
            },
        )
        row = result.fetchone()
        await db.commit()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create file checkpoint",
            )

        if row.status == 404:
            logger.info(f"pg-function: au_create_file_checkpoint() - status={row.status}, message={row.message}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=row.message,
            )

        return {"checkpoint_id": row.checkpoint_id}

    except HTTPException:
        await db.rollback()
        raise

    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create file checkpoint: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create file checkpoint.",
        )


@router.get(
    "/{file_id}",
    response_model=list[FileCheckpointRead],
    responses={
        500: {"description": "Internal server error"},
    },
)
async def get_file_checkpoint(
    file_id: uuid.UUID,
    checkpoint_id: uuid.UUID | None = Query(default=None, description="Checkpoint ID to filter"),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """
    Retrieve file checkpoint(s)

    - If checkpoint_id is provided, returns specific checkpoint
    - If checkpoint_id is not provided, returns all checkpoints for the file
    """

    try:
        result = await db.execute(
            text("""
                SELECT checkpoint_id, file_id, history_id,
                       original_text_modified, translated_text_modified, proofreaded_text,
                       created_at
                FROM au_get_file_checkpoint(:file_id, :checkpoint_id)
            """),
            {
                "file_id": file_id,
                "checkpoint_id": checkpoint_id,
            },
        )
        rows = result.fetchall()

        return [
            {
                "checkpoint_id": row.checkpoint_id,
                "file_id": row.file_id,
                "history_id": row.history_id,
                "original_text_modified": row.original_text_modified,
                "translated_text_modified": row.translated_text_modified,
                "proofreaded_text": row.proofreaded_text,
                "created_at": row.created_at,
            }
            for row in rows
        ]

    except Exception as e:
        logger.error(f"Failed to retrieve file checkpoint: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve file checkpoint.",
        )
