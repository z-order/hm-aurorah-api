"""
File ACL endpoints

Endpoint                              SQL Function
------------------------------------  ------------------
POST /                                au_create_file_acl()
GET /{file_id}                        au_get_file_acl()
PUT /                                 au_update_file_acl()
DELETE /{file_id}/{principal_id}      au_delete_file_acl()

SQL Function            Status Codes
----------------------  --------------------------
au_create_file_acl      200(OK), 409(Conflict), 404(Not Found)
au_update_file_acl      200(OK), 404(Not Found)
au_delete_file_acl      200(OK), 404(Not Found)
au_get_file_acl         (no status, returns rows)

See: scripts/schema-functions/schema-public.file.acl.sql
"""

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logger import get_logger
from app.models.file_acl import FileAclCreate, FileAclRead, FileAclUpdate

logger = get_logger(__name__, logging.INFO)

router: APIRouter = APIRouter()


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    responses={
        404: {"description": "File not found"},
        409: {"description": "ACL already exists for this principal"},
        500: {"description": "Internal server error"},
    },
)
async def create_file_acl(
    acl_data: FileAclCreate,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """
    Create new file ACL
    """

    try:
        result = await db.execute(
            text("""
                SELECT status, message
                FROM au_create_file_acl(:file_id, :principal_id, :role)
            """),
            {
                "file_id": acl_data.file_id,
                "principal_id": acl_data.principal_id,
                "role": acl_data.role,
            },
        )
        row = result.fetchone()
        await db.commit()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create file ACL",
            )

        if row.status == 404:
            logger.info(f"pg-function: au_create_file_acl() - status={row.status}, message={row.message}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=row.message,
            )

        if row.status == 409:
            logger.info(f"pg-function: au_create_file_acl() - status={row.status}, message={row.message}")
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
        logger.error(f"Failed to create file ACL: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create file ACL.",
        )


@router.get(
    "/{file_id}",
    response_model=list[FileAclRead],
    responses={
        500: {"description": "Internal server error"},
    },
)
async def get_file_acl(
    file_id: uuid.UUID,
    principal_id: uuid.UUID | None = Query(default=None, description="Principal ID to filter"),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """
    Retrieve file ACL(s)

    - If principal_id is provided, returns specific ACL
    - If principal_id is not provided, returns all ACLs for the file
    """

    try:
        result = await db.execute(
            text("""
                SELECT file_id, principal_id, role, created_at, updated_at
                FROM au_get_file_acl(:file_id, :principal_id)
            """),
            {
                "file_id": file_id,
                "principal_id": principal_id,
            },
        )
        rows = result.fetchall()

        return [
            {
                "file_id": row.file_id,
                "principal_id": row.principal_id,
                "role": row.role,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            }
            for row in rows
        ]

    except Exception as e:
        logger.error(f"Failed to retrieve file ACL: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve file ACL.",
        )


@router.put(
    "/",
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "File ACL not found"},
        500: {"description": "Internal server error"},
    },
)
async def update_file_acl(
    acl_data: FileAclUpdate,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """
    Update file ACL role
    """

    try:
        result = await db.execute(
            text("""
                SELECT status, message
                FROM au_update_file_acl(:file_id, :principal_id, :role)
            """),
            {
                "file_id": acl_data.file_id,
                "principal_id": acl_data.principal_id,
                "role": acl_data.role,
            },
        )
        row = result.fetchone()
        await db.commit()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update file ACL",
            )

        if row.status == 404:
            logger.info(f"pg-function: au_update_file_acl() - status={row.status}, message={row.message}")
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
        logger.error(f"Failed to update file ACL: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update file ACL.",
        )


@router.delete(
    "/{file_id}/{principal_id}",
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "File ACL not found"},
        500: {"description": "Internal server error"},
    },
)
async def delete_file_acl(
    file_id: uuid.UUID,
    principal_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """
    Delete file ACL
    """

    try:
        result = await db.execute(
            text("""
                SELECT status, message
                FROM au_delete_file_acl(:file_id, :principal_id)
            """),
            {
                "file_id": file_id,
                "principal_id": principal_id,
            },
        )
        row = result.fetchone()
        await db.commit()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete file ACL",
            )

        if row.status == 404:
            logger.info(f"pg-function: au_delete_file_acl() - status={row.status}, message={row.message}")
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
        logger.error(f"Failed to delete file ACL: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete file ACL.",
        )
