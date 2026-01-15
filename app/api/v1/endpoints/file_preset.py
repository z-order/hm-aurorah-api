"""
File preset endpoints

Endpoint                      SQL Function
----------------------------  ------------------
POST /                        au_create_file_preset()
GET /{principal_id}           au_get_file_preset()
PUT /{file_preset_id}         au_update_file_preset()
DELETE /{file_preset_id}      au_delete_file_preset()

SQL Function            Status Codes
----------------------  --------------------------
au_create_file_preset   200(OK), 409(Conflict)
au_update_file_preset   200(OK), 404(Not Found)
au_delete_file_preset   200(OK), 404(Not Found)
au_get_file_preset      (no status, returns rows)

See: scripts/schema-functions/schema-public.file.preset.sql
"""

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logger import get_logger
from app.models.file_preset import FilePresetCreate, FilePresetCreateResponse, FilePresetRead, FilePresetUpdate

logger = get_logger(__name__, logging.INFO)

router: APIRouter = APIRouter()


@router.post(
    "/",
    response_model=FilePresetCreateResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        409: {"description": "Preset with same description already exists"},
        500: {"description": "Internal server error"},
    },
)
async def create_file_preset(
    preset_data: FilePresetCreate,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Create new file preset
    """

    try:
        result = await db.execute(
            text("""
                SELECT status, message, file_preset_id
                FROM au_create_file_preset(
                    :principal_id,
                    :description,
                    :translation_memory,
                    :translation_role,
                    :translation_rule,
                    :target_language,
                    :target_country,
                    :target_city,
                    :task_type,
                    :audience,
                    :purpose
                )
            """),
            {
                "principal_id": preset_data.principal_id,
                "description": preset_data.description,
                "translation_memory": preset_data.translation_memory,
                "translation_role": preset_data.translation_role,
                "translation_rule": preset_data.translation_rule,
                "target_language": preset_data.target_language,
                "target_country": preset_data.target_country,
                "target_city": preset_data.target_city,
                "task_type": preset_data.task_type,
                "audience": preset_data.audience,
                "purpose": preset_data.purpose,
            },
        )
        row = result.fetchone()
        await db.commit()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create file preset",
            )

        if row.status == 409:
            logger.info(f"pg-function: au_create_file_preset() - status={row.status}, message={row.message}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=row.message,
            )

        return {"file_preset_id": row.file_preset_id}

    except HTTPException:
        await db.rollback()
        raise

    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create file preset: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create file preset.",
        )


@router.get(
    "/{principal_id}",
    response_model=list[FilePresetRead],
    responses={
        500: {"description": "Internal server error"},
    },
)
async def get_file_preset(
    principal_id: uuid.UUID,
    file_preset_id: uuid.UUID | None = Query(default=None, description="File preset ID to filter"),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """
    Retrieve file preset(s)

    - If file_preset_id is provided, returns specific preset
    - If file_preset_id is not provided, returns all presets for the principal
    """

    try:
        result = await db.execute(
            text("""
                SELECT file_preset_id, principal_id, description, translation_memory,
                       translation_role, translation_rule, target_language, target_country,
                       target_city, task_type, audience, purpose, created_at, updated_at
                FROM au_get_file_preset(:principal_id, :file_preset_id)
            """),
            {
                "principal_id": principal_id,
                "file_preset_id": file_preset_id,
            },
        )
        rows = result.fetchall()

        return [
            {
                "file_preset_id": row.file_preset_id,
                "principal_id": row.principal_id,
                "description": row.description,
                "translation_memory": row.translation_memory,
                "translation_role": row.translation_role,
                "translation_rule": row.translation_rule,
                "target_language": row.target_language,
                "target_country": row.target_country,
                "target_city": row.target_city,
                "task_type": row.task_type,
                "audience": row.audience,
                "purpose": row.purpose,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            }
            for row in rows
        ]

    except Exception as e:
        logger.error(f"Failed to retrieve file preset: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve file preset.",
        )


@router.put(
    "/{file_preset_id}",
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "File preset not found"},
        500: {"description": "Internal server error"},
    },
)
async def update_file_preset(
    file_preset_id: uuid.UUID,
    preset_data: FilePresetUpdate,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """
    Update file preset
    """

    try:
        result = await db.execute(
            text("""
                SELECT status, message
                FROM au_update_file_preset(
                    :file_preset_id,
                    :description,
                    :translation_memory,
                    :translation_role,
                    :translation_rule,
                    :target_language,
                    :target_country,
                    :target_city,
                    :task_type,
                    :audience,
                    :purpose
                )
            """),
            {
                "file_preset_id": file_preset_id,
                "description": preset_data.description,
                "translation_memory": preset_data.translation_memory,
                "translation_role": preset_data.translation_role,
                "translation_rule": preset_data.translation_rule,
                "target_language": preset_data.target_language,
                "target_country": preset_data.target_country,
                "target_city": preset_data.target_city,
                "task_type": preset_data.task_type,
                "audience": preset_data.audience,
                "purpose": preset_data.purpose,
            },
        )
        row = result.fetchone()
        await db.commit()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update file preset",
            )

        if row.status == 404:
            logger.info(f"pg-function: au_update_file_preset() - status={row.status}, message={row.message}")
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
        logger.error(f"Failed to update file preset: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update file preset.",
        )


@router.delete(
    "/{file_preset_id}",
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "File preset not found"},
        500: {"description": "Internal server error"},
    },
)
async def delete_file_preset(
    file_preset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """
    Delete file preset (soft delete)
    """

    try:
        result = await db.execute(
            text("""
                SELECT status, message
                FROM au_delete_file_preset(:file_preset_id)
            """),
            {"file_preset_id": file_preset_id},
        )
        row = result.fetchone()
        await db.commit()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete file preset",
            )

        if row.status == 404:
            logger.info(f"pg-function: au_delete_file_preset() - status={row.status}, message={row.message}")
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
        logger.error(f"Failed to delete file preset: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete file preset.",
        )
