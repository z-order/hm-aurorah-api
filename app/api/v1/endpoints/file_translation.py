"""
File translation endpoints

Endpoint                          SQL Function
--------------------------------  ------------------
POST /                            au_create_file_translation()
GET /{file_id}                    au_get_file_translation_for_listing()
GET /{file_id}/jsonb              au_get_file_translation_for_jsonb()
PUT /{translation_id}             au_update_file_translation()
DELETE /{translation_id}          au_delete_file_translation()

SQL Function                            Status Codes
--------------------------------------  --------------------------
au_create_file_translation              200(OK), 404(Not Found)
au_update_file_translation              200(OK), 404(Not Found)
au_delete_file_translation              200(OK), 404(Not Found)
au_get_file_translation_for_listing     (no status, returns rows)
au_get_file_translation_for_jsonb       (no status, returns rows)

See: scripts/schema-functions/schema-public.file.translation.sql
"""

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logger import get_logger
from app.models.file_translation import (
    FileTranslationCreate,
    FileTranslationCreateResponse,
    FileTranslationReadForJsonb,
    FileTranslationReadForListing,
    FileTranslationUpdate,
)

logger = get_logger(__name__, logging.INFO)

router: APIRouter = APIRouter()


@router.post(
    "/",
    response_model=FileTranslationCreateResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        404: {"description": "File not found"},
        500: {"description": "Internal server error"},
    },
)
async def create_file_translation(
    translation_data: FileTranslationCreate,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Create new file translation
    """

    try:
        result = await db.execute(
            text("""
                SELECT status, message, translation_id
                FROM au_create_file_translation(
                    :file_id,
                    :file_preset_id,
                    :file_preset_json,
                    :assignee_id,
                    :translated_text
                )
            """),
            {
                "file_id": translation_data.file_id,
                "file_preset_id": translation_data.file_preset_id,
                "file_preset_json": translation_data.file_preset_json,
                "assignee_id": translation_data.assignee_id,
                "translated_text": translation_data.translated_text,
            },
        )
        row = result.fetchone()
        await db.commit()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create file translation",
            )

        if row.status == 404:
            logger.info(f"pg-function: au_create_file_translation() - status={row.status}, message={row.message}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=row.message,
            )

        return {"translation_id": row.translation_id}

    except HTTPException:
        await db.rollback()
        raise

    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create file translation: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create file translation.",
        )


@router.get(
    "/{file_id}",
    response_model=list[FileTranslationReadForListing],
    responses={
        500: {"description": "Internal server error"},
    },
)
async def get_file_translation_for_listing(
    file_id: uuid.UUID,
    translation_id: uuid.UUID | None = Query(default=None, description="Translation ID to filter"),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """
    Retrieve file translation(s) for listing (without jsonb data)

    - If translation_id is provided, returns specific translation
    - If translation_id is not provided, returns all translations for the file
    """

    try:
        result = await db.execute(
            text("""
                SELECT translation_id, file_id, file_preset_id, file_preset_json,
                       assignee_id, created_at, updated_at
                FROM au_get_file_translation_for_listing(:file_id, :translation_id)
            """),
            {
                "file_id": file_id,
                "translation_id": translation_id,
            },
        )
        rows = result.fetchall()

        return [
            {
                "translation_id": row.translation_id,
                "file_id": row.file_id,
                "file_preset_id": row.file_preset_id,
                "file_preset_json": row.file_preset_json,
                "assignee_id": row.assignee_id,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            }
            for row in rows
        ]

    except Exception as e:
        logger.error(f"Failed to retrieve file translation: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve file translation.",
        )


@router.get(
    "/{file_id}/jsonb",
    response_model=list[FileTranslationReadForJsonb],
    responses={
        500: {"description": "Internal server error"},
    },
)
async def get_file_translation_for_jsonb(
    file_id: uuid.UUID,
    translation_id: uuid.UUID | None = Query(default=None, description="Translation ID to filter"),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """
    Retrieve file translation(s) with jsonb data

    - If translation_id is provided, returns specific translation
    - If translation_id is not provided, returns all translations for the file
    """

    try:
        result = await db.execute(
            text("""
                SELECT translation_id, file_id, file_preset_id, file_preset_json,
                       assignee_id, translated_text, translated_text_modified,
                       created_at, updated_at
                FROM au_get_file_translation_for_jsonb(:file_id, :translation_id)
            """),
            {
                "file_id": file_id,
                "translation_id": translation_id,
            },
        )
        rows = result.fetchall()

        return [
            {
                "translation_id": row.translation_id,
                "file_id": row.file_id,
                "file_preset_id": row.file_preset_id,
                "file_preset_json": row.file_preset_json,
                "assignee_id": row.assignee_id,
                "translated_text": row.translated_text,
                "translated_text_modified": row.translated_text_modified,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            }
            for row in rows
        ]

    except Exception as e:
        logger.error(f"Failed to retrieve file translation: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve file translation.",
        )


@router.put(
    "/{translation_id}",
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "File translation not found"},
        500: {"description": "Internal server error"},
    },
)
async def update_file_translation(
    translation_id: uuid.UUID,
    translation_data: FileTranslationUpdate,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """
    Update file translation
    """

    try:
        result = await db.execute(
            text("""
                SELECT status, message
                FROM au_update_file_translation(
                    :translation_id,
                    :translated_text,
                    :translated_text_modified
                )
            """),
            {
                "translation_id": translation_id,
                "translated_text": translation_data.translated_text,
                "translated_text_modified": translation_data.translated_text_modified,
            },
        )
        row = result.fetchone()
        await db.commit()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update file translation",
            )

        if row.status == 404:
            logger.info(f"pg-function: au_update_file_translation() - status={row.status}, message={row.message}")
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
        logger.error(f"Failed to update file translation: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update file translation.",
        )


@router.delete(
    "/{translation_id}",
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "File translation not found"},
        500: {"description": "Internal server error"},
    },
)
async def delete_file_translation(
    translation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """
    Delete file translation (soft delete)
    """

    try:
        result = await db.execute(
            text("""
                SELECT status, message
                FROM au_delete_file_translation(:translation_id)
            """),
            {"translation_id": translation_id},
        )
        row = result.fetchone()
        await db.commit()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete file translation",
            )

        if row.status == 404:
            logger.info(f"pg-function: au_delete_file_translation() - status={row.status}, message={row.message}")
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
        logger.error(f"Failed to delete file translation: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete file translation.",
        )
