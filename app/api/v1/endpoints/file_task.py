"""
File task endpoints

Endpoint                        SQL Function
------------------------------  ------------------
POST /open/{file_id}            au_get_file_task() -> au_get_file_task() -> au_create_file_task()
POST /                          au_create_file_task()
GET /{file_id}                  au_get_file_task()
GET /{file_id}/details          au_get_file_task_with_details()
PUT /{file_id}                  au_update_file_task()

SQL Function                    Status Codes
------------------------------  --------------------------
au_create_file_task             200(OK), 409(Conflict), 404(Not Found)
au_update_file_task             200(OK), 404(Not Found)
au_get_file_task                (no status, returns rows)
au_get_file_task_with_details   (no status, returns rows)

See: scripts/schema-functions/schema-public.file.task.sql
"""

import json
import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logger import get_logger
from app.models.file_task import FileTaskCreate, FileTaskRead, FileTaskReadWithDetails, FileTaskUpdate
from app.utils.utils_http import read_raw_text_file_from_url
from app.utils.utils_text import analyze_raw_text_to_json

logger = get_logger(__name__, logging.INFO)

router: APIRouter = APIRouter()


@router.post(
    "/open/{file_id}",
    response_model=FileTaskRead,
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "File not found"},
        422: {"description": "File has no URL"},
        500: {"description": "Internal server error"},
        502: {"description": "Failed to read file from CDN server"},
    },
)
async def open_file_task(
    file_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Open file task (get existing or create new)

    1. Try to get existing file task
    2. If not found, get file_url from au_file_nodes
    3. Read original_text from file_url
    4. Create new file task with original_text
    5. Return the file task
    """

    # Step 1: Try to get existing file task
    try:
        return await get_file_task(file_id, db)
    except HTTPException as e:
        if e.status_code != status.HTTP_404_NOT_FOUND:
            raise

    # Step 2: Task not found, get file_url from au_file_nodes
    try:
        result = await db.execute(
            text("""
                SELECT file_id, file_url FROM au_file_nodes
                WHERE file_id = :file_id AND deleted_at IS NULL
            """),
            {"file_id": file_id},
        )
        file_row = result.fetchone()

        if not file_row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found",
            )

        if not file_row.file_url:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="File has no URL",
            )

        # Step 3: Read raw text from file_url and analyze to JSON
        raw_text = await read_raw_text_file_from_url(file_row.file_url)
        original_text = analyze_raw_text_to_json(raw_text)

        # Step 4: Create new file task with original_text
        file_task_data = FileTaskCreate(file_id=file_id, original_text=original_text)
        await create_file_task(file_task_data, db)

        # Step 5: Return newly created file task
        return await get_file_task(file_id, db)

    except HTTPException:  # 502 from read_raw_text_file_from_url()
        raise

    except Exception as e:
        logger.error(f"Failed to open file task: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to open file task.",
        )


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    responses={
        404: {"description": "File not found"},
        409: {"description": "Task already exists for this file"},
        500: {"description": "Internal server error"},
    },
)
async def create_file_task(
    task_data: FileTaskCreate,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """
    Create new file task
    """

    try:
        result = await db.execute(
            text("""
                SELECT status, message
                FROM au_create_file_task(:file_id, :file_preset_id, :original_text)
            """),
            {
                "file_id": task_data.file_id,
                "file_preset_id": task_data.file_preset_id,
                "original_text": json.dumps(task_data.original_text),
            },
        )
        row = result.fetchone()
        await db.commit()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create file task",
            )

        if row.status == 404:
            logger.info(f"pg-function: au_create_file_task() - status={row.status}, message={row.message}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=row.message,
            )

        if row.status == 409:
            logger.info(f"pg-function: au_create_file_task() - status={row.status}, message={row.message}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=row.message,
            )

        return {"message": row.message}

    except HTTPException:
        await db.rollback()
        raise

    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create file task: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create file task.",
        )


@router.get(
    "/{file_id}",
    response_model=FileTaskRead,
    responses={
        404: {"description": "File task not found"},
        500: {"description": "Internal server error"},
    },
)
async def get_file_task(
    file_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Retrieve file task
    """

    try:
        result = await db.execute(
            text("""
                SELECT file_id, file_preset_id, original_id,
                       translation_id_1st, translation_id_2nd, proofreading_id,
                       created_at, updated_at
                FROM au_get_file_task(:file_id)
            """),
            {"file_id": file_id},
        )
        row = result.fetchone()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File task not found",
            )

        return {
            "file_id": row.file_id,
            "file_preset_id": row.file_preset_id,
            "original_id": row.original_id,
            "translation_id_1st": row.translation_id_1st,
            "translation_id_2nd": row.translation_id_2nd,
            "proofreading_id": row.proofreading_id,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to retrieve file task: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve file task.",
        )


@router.get(
    "/{file_id}/details",
    response_model=FileTaskReadWithDetails,
    responses={
        404: {"description": "File task not found"},
        500: {"description": "Internal server error"},
    },
)
async def get_file_task_with_details(
    file_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Retrieve file task with details (includes original text)
    """

    try:
        result = await db.execute(
            text("""
                SELECT file_id, file_preset_id, original_id,
                       original_text, original_text_modified,
                       translation_id_1st, translation_id_2nd, proofreading_id,
                       file_type, file_name, file_url, file_ext, file_size, mime_type, description,
                       created_at, updated_at
                FROM au_get_file_task_with_details(:file_id)
            """),
            {"file_id": file_id},
        )
        row = result.fetchone()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File task not found",
            )

        return {
            "file_id": row.file_id,
            "file_preset_id": row.file_preset_id,
            "original_id": row.original_id,
            "original_text": row.original_text,
            "original_text_modified": row.original_text_modified,
            "translation_id_1st": row.translation_id_1st,
            "translation_id_2nd": row.translation_id_2nd,
            "proofreading_id": row.proofreading_id,
            "file_type": row.file_type,
            "file_name": row.file_name,
            "file_url": row.file_url,
            "file_ext": row.file_ext,
            "file_size": row.file_size,
            "mime_type": row.mime_type,
            "description": row.description,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to retrieve file task with details: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve file task with details.",
        )


@router.put(
    "/{file_id}",
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "File task not found"},
        500: {"description": "Internal server error"},
    },
)
async def update_file_task(
    file_id: uuid.UUID,
    task_data: FileTaskUpdate,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """
    Update file task
    """

    try:
        result = await db.execute(
            text("""
                SELECT status, message
                FROM au_update_file_task(
                    :file_id,
                    :file_preset_id,
                    :translation_id_1st,
                    :translation_id_2nd,
                    :proofreading_id
                )
            """),
            {
                "file_id": file_id,
                "file_preset_id": task_data.file_preset_id,
                "translation_id_1st": task_data.translation_id_1st,
                "translation_id_2nd": task_data.translation_id_2nd,
                "proofreading_id": task_data.proofreading_id,
            },
        )
        row = result.fetchone()
        await db.commit()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update file task",
            )

        if row.status == 404:
            logger.info(f"pg-function: au_update_file_task() - status={row.status}, message={row.message}")
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
        logger.error(f"Failed to update file task: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update file task.",
        )
