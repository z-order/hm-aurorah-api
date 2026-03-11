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

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from uuid_utils import uuid7

from app.core.database import get_db
from app.core.logger import get_logger
from app.models.file_task import FileTaskCreate, FileTaskRead, FileTaskReadWithDetails, FileTaskUpdate
from app.utils.utils_file_validate import (
    SYNC_CATEGORIES,
    ZIP_CATEGORIES,
    validate_file_extension,
    validate_file_magic_bytes,
)
from app.utils.utils_http import read_binary_file_from_url, read_file_header_from_url, read_raw_text_file_from_url
from app.utils.utils_text import analyze_raw_text_to_json

from .file_task_extract import bg_atask_extract_file_text
from .file_task_helpers import update_file_node_status

logger = get_logger(__name__, logging.INFO)

router: APIRouter = APIRouter()


@router.post(
    "/open/{file_id}",
    response_model=FileTaskRead,
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "File not found"},
        422: {"description": "File has no URL or unsupported file type"},
        500: {"description": "Internal server error"},
        502: {"description": "Failed to read file from CDN server"},
    },
)
async def open_file_task(
    file_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Open file task (get existing or create new)

    1. Try to get existing file task
    2. If not found, get file_url and file_ext from au_file_nodes
    3. Validate file type (extension + magic bytes)
    4a. Sync path (text files): extract inline, create task, return
    4b. Async path (docx/pptx/xlsx/hwpx/pdf/epub/video): create task with
        placeholder, launch background extraction, return with rsmq_channel_id
    """

    # Step 1: Try to get existing file task
    try:
        return await get_file_task(file_id, db)
    except HTTPException as e:
        if e.status_code != status.HTTP_404_NOT_FOUND:
            raise

    # Step 2: Task not found, get file_url and file_ext from au_file_nodes
    try:
        result = await db.execute(
            text("""
                SELECT file_id, file_url, file_ext FROM au_file_nodes
                WHERE file_id = :file_id AND deleted_at IS NULL
            """),
            {"file_id": file_id},
        )
        file_row = result.fetchone()

        if not file_row:
            detail = "File not found"
            logger.warning(f"open_file_task: file_id={file_id}, 404={detail}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

        if not file_row.file_url:
            detail = "File has no URL"
            logger.warning(f"open_file_task: file_id={file_id}, 422={detail}")
            await update_file_node_status(file_id, "failed", detail, db)
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)

        # Step 3: Validate file type
        try:
            category = validate_file_extension(file_row.file_ext)
        except ValueError as e:
            detail = str(e)
            logger.warning(f"open_file_task: file_id={file_id}, 422={detail}")
            await update_file_node_status(file_id, "failed", detail, db)
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)

        # Step 3b: Magic bytes validation for non-text files
        file_content_for_extract: bytes | None = None
        if category not in SYNC_CATEGORIES:
            if category in ZIP_CATEGORIES:
                file_content_for_extract = await read_binary_file_from_url(file_row.file_url)
                file_header = file_content_for_extract
            else:
                file_header = await read_file_header_from_url(file_row.file_url)
            if not validate_file_magic_bytes(file_header, file_row.file_ext):
                detail = f"File content does not match extension {file_row.file_ext}"
                logger.warning(f"open_file_task: file_id={file_id}, 422={detail}")
                await update_file_node_status(file_id, "failed", detail, db)
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)

        # =====================================================================
        # Step 4a: SYNC PATH (text files)
        # =====================================================================
        if category in SYNC_CATEGORIES:
            # Read raw text from file_url and analyze to JSON
            raw_text = await read_raw_text_file_from_url(file_row.file_url)
            original_text = analyze_raw_text_to_json(raw_text)

            # Create new file task with original_text
            file_task_data = FileTaskCreate(file_id=file_id, original_text=original_text)
            await create_file_task(file_task_data, db)

            # Return newly created file task
            return await get_file_task(file_id, db)

        # =====================================================================
        # Step 4b: ASYNC PATH (docx/pptx/xlsx/hwpx/pdf/epub/video)
        # =====================================================================
        placeholder_text: dict[str, Any] = {"segments": []}
        file_task_data = FileTaskCreate(file_id=file_id, original_text=placeholder_text)
        await create_file_task(file_task_data, db)

        task_data = await get_file_task(file_id, db)

        rsmq_channel_id = str(uuid7())

        background_tasks.add_task(
            bg_atask_extract_file_text,
            rsmq_channel_id=rsmq_channel_id,
            file_id=file_id,
            original_id=task_data["original_id"],
            file_url=file_row.file_url,
            file_ext=file_row.file_ext,
            file_content=file_content_for_extract,
        )

        task_data["rsmq_channel_id"] = rsmq_channel_id
        return task_data

    except HTTPException:  # Re-raise 404/422/502 from validation or read_raw_text_file_from_url
        raise

    except Exception as e:
        msg = "Failed to open file task"
        logger.error(f"{msg}: {e}", exc_info=True)
        await update_file_node_status(file_id, "failed", msg, db)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=msg)


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
            detail = "Failed to create file task (no row returned)"
            logger.error(f"create_file_task: 500={detail}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)

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
        msg = "Failed to create file task"
        logger.error(f"{msg}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=msg)


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
            detail = "File task not found"
            logger.warning(f"get_file_task: file_id={file_id}, 404={detail}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

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
        msg = "Failed to retrieve file task"
        logger.error(f"{msg}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=msg)


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
                       file_status, file_message,
                       created_at, updated_at
                FROM au_get_file_task_with_details(:file_id)
            """),
            {"file_id": file_id},
        )
        row = result.fetchone()

        if not row:
            detail = "File task not found"
            logger.warning(f"get_file_task_with_details: file_id={file_id}, 404={detail}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

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
            "status": row.file_status,
            "message": row.file_message,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }

    except HTTPException:
        raise

    except Exception as e:
        msg = "Failed to retrieve file task with details"
        logger.error(f"{msg}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=msg)


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
            detail = "Failed to update file task (no row returned)"
            logger.error(f"update_file_task: 500={detail}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)

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
        msg = "Failed to update file task"
        logger.error(f"{msg}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=msg)
