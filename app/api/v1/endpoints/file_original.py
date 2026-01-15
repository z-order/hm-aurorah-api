"""
File original endpoints

Endpoint                    SQL Function
--------------------------  ------------------
POST /                      au_create_file_original()
GET /                       au_get_file_original()
PUT /{original_id}          au_update_file_original()

SQL Function              Status Codes
------------------------  --------------------------
au_create_file_original   200(OK), 409(Conflict), 404(Not Found)
au_update_file_original   200(OK), 404(Not Found)
au_get_file_original      (no status, returns rows)

See: scripts/schema-functions/schema-public.file.original.sql
"""

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logger import get_logger
from app.models.file_original import (
    FileOriginalCreate,
    FileOriginalCreateResponse,
    FileOriginalRead,
    FileOriginalUpdate,
)

logger = get_logger(__name__, logging.INFO)

router: APIRouter = APIRouter()


@router.post(
    "/",
    response_model=FileOriginalCreateResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        404: {"description": "File not found"},
        409: {"description": "Original text already exists for this file"},
        500: {"description": "Internal server error"},
    },
)
async def create_file_original(
    original_data: FileOriginalCreate,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Create new file original
    """

    try:
        result = await db.execute(
            text("""
                SELECT status, message, original_id
                FROM au_create_file_original(:file_id, :original_text)
            """),
            {
                "file_id": original_data.file_id,
                "original_text": original_data.original_text,
            },
        )
        row = result.fetchone()
        await db.commit()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create file original",
            )

        if row.status == 404:
            logger.info(f"pg-function: au_create_file_original() - status={row.status}, message={row.message}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=row.message,
            )

        if row.status == 409:
            logger.info(f"pg-function: au_create_file_original() - status={row.status}, message={row.message}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=row.message,
            )

        return {"original_id": row.original_id}

    except HTTPException:
        await db.rollback()
        raise

    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create file original: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create file original.",
        )


@router.get(
    "/",
    response_model=list[FileOriginalRead],
    responses={
        500: {"description": "Internal server error"},
    },
)
async def get_file_original(
    file_id: uuid.UUID | None = Query(default=None, description="File ID to filter"),
    original_id: uuid.UUID | None = Query(default=None, description="Original ID to filter"),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """
    Retrieve file original

    - If file_id is provided, returns original by file_id
    - If original_id is provided, returns original by original_id
    """

    try:
        result = await db.execute(
            text("""
                SELECT original_id, file_id, original_text, original_text_modified,
                       created_at, updated_at
                FROM au_get_file_original(:file_id, :original_id)
            """),
            {
                "file_id": file_id,
                "original_id": original_id,
            },
        )
        rows = result.fetchall()

        return [
            {
                "original_id": row.original_id,
                "file_id": row.file_id,
                "original_text": row.original_text,
                "original_text_modified": row.original_text_modified,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            }
            for row in rows
        ]

    except Exception as e:
        logger.error(f"Failed to retrieve file original: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve file original.",
        )


@router.put(
    "/{original_id}",
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "File original not found"},
        500: {"description": "Internal server error"},
    },
)
async def update_file_original(
    original_id: uuid.UUID,
    original_data: FileOriginalUpdate,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """
    Update file original
    """

    try:
        result = await db.execute(
            text("""
                SELECT status, message
                FROM au_update_file_original(:original_id, :original_text, :original_text_modified)
            """),
            {
                "original_id": original_id,
                "original_text": original_data.original_text,
                "original_text_modified": original_data.original_text_modified,
            },
        )
        row = result.fetchone()
        await db.commit()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update file original",
            )

        if row.status == 404:
            logger.info(f"pg-function: au_update_file_original() - status={row.status}, message={row.message}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=row.message,
            )

        return {"message": row.message}

    except HTTPException:
        await db.rollback()
        raise

    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to update file original: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update file original.",
        )
