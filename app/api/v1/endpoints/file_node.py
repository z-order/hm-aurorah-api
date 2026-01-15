"""
File node endpoints

Endpoint                    SQL Function
--------------------------  ------------------
POST /                      au_create_file()
GET /{owner_id}             au_get_files()
PUT /{file_id}              au_update_file()
DELETE /{file_id}           au_delete_file()
POST /{file_id}/duplicate   au_duplicate_file()
PUT /{file_id}/move         au_move_file()

SQL Function          Status Codes
--------------------  --------------------------
au_create_file        200(OK), 409(Conflict), 404(Not Found)
au_update_file        200(OK), 409(Conflict), 404(Not Found)
au_delete_file        200(OK), 404(Not Found)
au_duplicate_file     200(OK), 404(Not Found)
au_move_file          200(OK), 409(Conflict), 404(Not Found)
au_get_files          (no status, returns rows)

All error codes from SQL functions are properly mapped to HTTP exceptions.

See: scripts/schema-functions/schema-public.file.file.sql
"""

import logging
import uuid
from enum import Enum
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logger import get_logger
from app.models.file_node import (
    FileNodeCreate,
    FileNodeCreateResponse,
    FileNodeDuplicateResponse,
    FileNodeMove,
    FileNodeRead,
    FileNodeUpdate,
)

logger = get_logger(__name__, logging.INFO)

router: APIRouter = APIRouter()


class FileGetOption(str, Enum):
    """File get option for au_get_files"""

    ALL_FILES = "all-files"
    SHARED_FILES = "shared-files"
    TRASH_FILES = "trash-files"
    NODES = "nodes"


#
# CRUD for File Nodes
#


@router.post(
    "/",
    response_model=FileNodeCreateResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        404: {"description": "Parent folder not found"},
        409: {"description": "Folder/file name already exists"},
        500: {"description": "Internal server error"},
    },
)
async def create_file_node(
    file_node_data: FileNodeCreate,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Create new file node (folder or file)
    """

    try:
        result = await db.execute(
            text("""
                SELECT status, message, file_id
                FROM au_create_file(
                    :owner_id,
                    :parent_file_id,
                    :file_type,
                    :file_name,
                    :file_url,
                    :file_ext,
                    :file_size,
                    :mime_type,
                    :description
                )
            """),
            {
                "owner_id": file_node_data.owner_id,
                "parent_file_id": file_node_data.parent_file_id,
                "file_type": file_node_data.file_type.value,
                "file_name": file_node_data.file_name,
                "file_url": file_node_data.file_url,
                "file_ext": file_node_data.file_ext,
                "file_size": file_node_data.file_size,
                "mime_type": file_node_data.mime_type,
                "description": file_node_data.description,
            },
        )
        row = result.fetchone()
        await db.commit()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create file node",
            )

        if row.status == 404:
            logger.info(f"pg-function: au_create_file() - status={row.status}, message={row.message}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=row.message,
            )

        if row.status == 409:
            logger.info(f"pg-function: au_create_file() - status={row.status}, message={row.message}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=row.message,
            )

        return {"file_id": row.file_id}

    except HTTPException:
        await db.rollback()
        raise

    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create file node: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create file node.",
        )


@router.get(
    "/{owner_id}",
    response_model=list[FileNodeRead],
    responses={
        500: {"description": "Internal server error"},
    },
)
async def get_file_nodes(
    owner_id: str,
    option: FileGetOption = Query(default=FileGetOption.NODES, description="File get option"),
    parent_file_id: uuid.UUID | None = Query(default=None, description="Parent file ID for nodes option"),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """
    Retrieve file nodes

    Options:
    - all-files: Get all files owned by user
    - shared-files: Get files shared with user
    - trash-files: Get deleted files (trash)
    - nodes: Get root nodes or child nodes of a parent folder
    """

    try:
        result = await db.execute(
            text("""
                SELECT file_id, owner_id, parent_file_id, file_type,
                       file_name, file_url, file_ext, file_size,
                       mime_type, description, created_at, updated_at, deleted_at
                FROM au_get_files(:owner_id, :option, :parent_file_id)
            """),
            {
                "owner_id": owner_id,
                "option": option.value,
                "parent_file_id": parent_file_id,
            },
        )
        rows = result.fetchall()

        return [
            {
                "file_id": row.file_id,
                "owner_id": row.owner_id,
                "parent_file_id": row.parent_file_id,
                "file_type": row.file_type,
                "file_name": row.file_name,
                "file_url": row.file_url,
                "file_ext": row.file_ext,
                "file_size": row.file_size,
                "mime_type": row.mime_type,
                "description": row.description,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
                "deleted_at": row.deleted_at,
            }
            for row in rows
        ]

    except Exception as e:
        logger.error(f"Failed to retrieve file nodes: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve file nodes.",
        )


@router.put(
    "/{file_id}",
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "File not found"},
        409: {"description": "Folder/file name already exists"},
        500: {"description": "Internal server error"},
    },
)
async def update_file_node(
    file_id: uuid.UUID,
    file_node_data: FileNodeUpdate,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """
    Update file node (file_name, description)
    """

    try:
        result = await db.execute(
            text("""
                SELECT status, message
                FROM au_update_file(:file_id, :file_name, :description)
            """),
            {
                "file_id": file_id,
                "file_name": file_node_data.file_name,
                "description": file_node_data.description,
            },
        )
        row = result.fetchone()
        await db.commit()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update file node",
            )

        if row.status == 404:
            logger.info(f"pg-function: au_update_file() - status={row.status}, message={row.message}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=row.message,
            )

        if row.status == 409:
            logger.info(f"pg-function: au_update_file() - status={row.status}, message={row.message}")
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
        logger.error(f"Failed to update file node: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update file node.",
        )


@router.delete(
    "/{file_id}",
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "File not found"},
        500: {"description": "Internal server error"},
    },
)
async def delete_file_node(
    file_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """
    Delete file node (soft delete)
    """

    try:
        result = await db.execute(
            text("""
                SELECT status, message
                FROM au_delete_file(:file_id)
            """),
            {"file_id": file_id},
        )
        row = result.fetchone()
        await db.commit()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete file node",
            )

        if row.status == 404:
            logger.info(f"pg-function: au_delete_file() -  status={row.status}, message={row.message}")
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
        logger.error(f"Failed to delete file node: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete file node.",
        )


@router.post(
    "/{file_id}/duplicate",
    response_model=FileNodeDuplicateResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        404: {"description": "File not found"},
        500: {"description": "Internal server error"},
    },
)
async def duplicate_file_node(
    file_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Duplicate file node in the same folder
    """

    try:
        result = await db.execute(
            text("""
                SELECT status, message, file_id
                FROM au_duplicate_file(:file_id)
            """),
            {"file_id": file_id},
        )
        row = result.fetchone()
        await db.commit()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to duplicate file node",
            )

        if row.status == 404:
            logger.info(f"pg-function: au_duplicate_file() - status={row.status}, message={row.message}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=row.message,
            )

        return {"file_id": row.file_id}

    except HTTPException:
        await db.rollback()
        raise

    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to duplicate file node: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to duplicate file node.",
        )


@router.put(
    "/{file_id}/move",
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "File not found / Parent folder not found"},
        409: {"description": "Folder/file name already exists"},
        500: {"description": "Internal server error"},
    },
)
async def move_file_node(
    file_id: uuid.UUID,
    move_data: FileNodeMove,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """
    Move file node to a new parent folder
    """

    try:
        result = await db.execute(
            text("""
                SELECT status, message
                FROM au_move_file(:file_id, :new_parent_file_id)
            """),
            {
                "file_id": file_id,
                "new_parent_file_id": move_data.new_parent_file_id,
            },
        )
        row = result.fetchone()
        await db.commit()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to move file node",
            )

        if row.status == 404:
            logger.info(f"pg-function: au_move_file() - status={row.status}, message={row.message}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=row.message,
            )

        if row.status == 409:
            logger.info(f"pg-function: au_move_file() - status={row.status}, message={row.message}")
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
        logger.error(f"Failed to move file node: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to move file node.",
        )
