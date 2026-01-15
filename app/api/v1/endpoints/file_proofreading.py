"""
File proofreading endpoints

Endpoint                            SQL Function
----------------------------------  ------------------
POST /                              au_create_file_proofreading()
GET /{file_id}                      au_get_file_proofreading_for_listing()
GET /{file_id}/jsonb                au_get_file_proofreading_for_jsonb()
PUT /{proofreading_id}              au_update_file_proofreading()
DELETE /{proofreading_id}           au_delete_file_proofreading()

SQL Function                              Status Codes
----------------------------------------  --------------------------
au_create_file_proofreading               200(OK), 404(Not Found)
au_update_file_proofreading               200(OK), 404(Not Found)
au_delete_file_proofreading               200(OK), 404(Not Found)
au_get_file_proofreading_for_listing      (no status, returns rows)
au_get_file_proofreading_for_jsonb        (no status, returns rows)

See: scripts/schema-functions/schema-public.file.proofreading.sql
"""

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logger import get_logger
from app.models.file_proofreading import (
    FileProofreadingCreate,
    FileProofreadingCreateResponse,
    FileProofreadingReadForJsonb,
    FileProofreadingReadForListing,
    FileProofreadingUpdate,
)

logger = get_logger(__name__, logging.INFO)

router: APIRouter = APIRouter()


@router.post(
    "/",
    response_model=FileProofreadingCreateResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        404: {"description": "File not found"},
        500: {"description": "Internal server error"},
    },
)
async def create_file_proofreading(
    proofreading_data: FileProofreadingCreate,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Create new file proofreading
    """

    try:
        result = await db.execute(
            text("""
                SELECT status, message, proofreading_id
                FROM au_create_file_proofreading(
                    :file_id,
                    :assignee_id,
                    :participant_ids,
                    :proofreaded_text
                )
            """),
            {
                "file_id": proofreading_data.file_id,
                "assignee_id": proofreading_data.assignee_id,
                "participant_ids": proofreading_data.participant_ids,
                "proofreaded_text": proofreading_data.proofreaded_text,
            },
        )
        row = result.fetchone()
        await db.commit()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create file proofreading",
            )

        if row.status == 404:
            logger.info(f"pg-function: au_create_file_proofreading() - status={row.status}, message={row.message}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=row.message,
            )

        return {"proofreading_id": row.proofreading_id}

    except HTTPException:
        await db.rollback()
        raise

    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create file proofreading: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create file proofreading.",
        )


@router.get(
    "/{file_id}",
    response_model=list[FileProofreadingReadForListing],
    responses={
        500: {"description": "Internal server error"},
    },
)
async def get_file_proofreading_for_listing(
    file_id: uuid.UUID,
    proofreading_id: uuid.UUID | None = Query(default=None, description="Proofreading ID to filter"),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """
    Retrieve file proofreading(s) for listing (without jsonb data)

    - If proofreading_id is provided, returns specific proofreading
    - If proofreading_id is not provided, returns all proofreadings for the file
    """

    try:
        result = await db.execute(
            text("""
                SELECT proofreading_id, file_id, assignee_id, participant_ids,
                       created_at, updated_at
                FROM au_get_file_proofreading_for_listing(:file_id, :proofreading_id)
            """),
            {
                "file_id": file_id,
                "proofreading_id": proofreading_id,
            },
        )
        rows = result.fetchall()

        return [
            {
                "proofreading_id": row.proofreading_id,
                "file_id": row.file_id,
                "assignee_id": row.assignee_id,
                "participant_ids": row.participant_ids,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            }
            for row in rows
        ]

    except Exception as e:
        logger.error(f"Failed to retrieve file proofreading: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve file proofreading.",
        )


@router.get(
    "/{file_id}/jsonb",
    response_model=list[FileProofreadingReadForJsonb],
    responses={
        500: {"description": "Internal server error"},
    },
)
async def get_file_proofreading_for_jsonb(
    file_id: uuid.UUID,
    proofreading_id: uuid.UUID | None = Query(default=None, description="Proofreading ID to filter"),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """
    Retrieve file proofreading(s) with jsonb data

    - If proofreading_id is provided, returns specific proofreading
    - If proofreading_id is not provided, returns all proofreadings for the file
    """

    try:
        result = await db.execute(
            text("""
                SELECT proofreading_id, file_id, assignee_id, participant_ids,
                       proofreaded_text, created_at, updated_at
                FROM au_get_file_proofreading_for_jsonb(:file_id, :proofreading_id)
            """),
            {
                "file_id": file_id,
                "proofreading_id": proofreading_id,
            },
        )
        rows = result.fetchall()

        return [
            {
                "proofreading_id": row.proofreading_id,
                "file_id": row.file_id,
                "assignee_id": row.assignee_id,
                "participant_ids": row.participant_ids,
                "proofreaded_text": row.proofreaded_text,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            }
            for row in rows
        ]

    except Exception as e:
        logger.error(f"Failed to retrieve file proofreading: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve file proofreading.",
        )


@router.put(
    "/{proofreading_id}",
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "File proofreading not found"},
        500: {"description": "Internal server error"},
    },
)
async def update_file_proofreading(
    proofreading_id: uuid.UUID,
    proofreading_data: FileProofreadingUpdate,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """
    Update file proofreading
    """

    try:
        result = await db.execute(
            text("""
                SELECT status, message
                FROM au_update_file_proofreading(
                    :proofreading_id,
                    :assignee_id,
                    :participant_ids,
                    :proofreaded_text
                )
            """),
            {
                "proofreading_id": proofreading_id,
                "assignee_id": proofreading_data.assignee_id,
                "participant_ids": proofreading_data.participant_ids,
                "proofreaded_text": proofreading_data.proofreaded_text,
            },
        )
        row = result.fetchone()
        await db.commit()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update file proofreading",
            )

        if row.status == 404:
            logger.info(f"pg-function: au_update_file_proofreading() - status={row.status}, message={row.message}")
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
        logger.error(f"Failed to update file proofreading: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update file proofreading.",
        )


@router.delete(
    "/{proofreading_id}",
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "File proofreading not found"},
        500: {"description": "Internal server error"},
    },
)
async def delete_file_proofreading(
    proofreading_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """
    Delete file proofreading (soft delete)
    """

    try:
        result = await db.execute(
            text("""
                SELECT status, message
                FROM au_delete_file_proofreading(:proofreading_id)
            """),
            {"proofreading_id": proofreading_id},
        )
        row = result.fetchone()
        await db.commit()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete file proofreading",
            )

        if row.status == 404:
            logger.info(f"pg-function: au_delete_file_proofreading() - status={row.status}, message={row.message}")
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
        logger.error(f"Failed to delete file proofreading: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete file proofreading.",
        )
