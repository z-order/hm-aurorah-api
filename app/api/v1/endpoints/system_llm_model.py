"""
System LLM model endpoints

Endpoint                      SQL Function
----------------------------  ------------------
POST /upsert                  au_system_upsert_llm_model()
POST /                        au_system_create_llm_model()
GET /                         au_system_get_llm_model()
PUT /{llm_model_id}           au_system_update_llm_model()
DELETE /{llm_model_id}        au_system_delete_llm_model()

SQL Function                  Status Codes
----------------------------  --------------------------
au_system_upsert_llm_model    200(OK/Updated), 201(Created)
au_system_create_llm_model    200(OK), 409(Conflict)
au_system_update_llm_model    200(OK), 404(Not Found)
au_system_delete_llm_model    200(OK), 404(Not Found)
au_system_get_llm_model       (no status, returns rows)

See: scripts/schema-functions/schema-public.system.llm-model.sql
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logger import get_logger
from app.models.system_llm_model import (
    SystemLlmModelCreate,
    SystemLlmModelRead,
    SystemLlmModelUpdate,
    SystemLlmModelUpsert,
)

logger = get_logger(__name__, logging.INFO)

router: APIRouter = APIRouter()


@router.post(
    "/upsert",
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "LLM model updated or already exists"},
        201: {"description": "LLM model created"},
        500: {"description": "Internal server error"},
    },
)
async def upsert_llm_model(
    model_data: SystemLlmModelUpsert,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Upsert LLM model (insert or update)

    - If model does not exist, creates new one (returns 201)
    - If model exists with different values, updates it (returns 200)
    - If model exists with same values, no change (returns 200)
    - If model was soft-deleted, resurrects it
    """

    try:
        result = await db.execute(
            text("""
                SELECT status, message
                FROM au_system_upsert_llm_model(:llm_model_id, :llm_model_title, :llm_model_keyword, :ui_sort_order, :description, :provider)
            """),
            {
                "llm_model_id": model_data.llm_model_id,
                "llm_model_title": model_data.llm_model_title,
                "llm_model_keyword": model_data.llm_model_keyword,
                "ui_sort_order": model_data.ui_sort_order,
                "description": model_data.description,
                "provider": model_data.provider,
            },
        )
        row = result.fetchone()
        await db.commit()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upsert LLM model",
            )

        # Set HTTP response status code from SQL function result
        response.status_code = row.status

        return {"status": row.status, "message": row.message}

    except HTTPException:
        await db.rollback()
        raise

    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to upsert LLM model: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upsert LLM model.",
        )


@router.post(
    "/",
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "LLM model created"},
        409: {"description": "LLM model already exists"},
        500: {"description": "Internal server error"},
    },
)
async def create_llm_model(
    model_data: SystemLlmModelCreate,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Create new LLM model
    """

    try:
        result = await db.execute(
            text("""
                SELECT status, message
                FROM au_system_create_llm_model(:llm_model_id, :llm_model_title, :llm_model_keyword, :ui_sort_order, :description, :provider)
            """),
            {
                "llm_model_id": model_data.llm_model_id,
                "llm_model_title": model_data.llm_model_title,
                "llm_model_keyword": model_data.llm_model_keyword,
                "ui_sort_order": model_data.ui_sort_order,
                "description": model_data.description,
                "provider": model_data.provider,
            },
        )
        row = result.fetchone()
        await db.commit()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create LLM model",
            )

        # Set HTTP response status code from SQL function result
        response.status_code = row.status

        if row.status == 409:
            logger.info(f"pg-function: au_system_create_llm_model() - status={row.status}, message={row.message}")

        return {"status": row.status, "message": row.message}

    except HTTPException:
        await db.rollback()
        raise

    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create LLM model: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create LLM model.",
        )


@router.get(
    "/",
    response_model=list[SystemLlmModelRead],
    responses={
        500: {"description": "Internal server error"},
    },
)
async def get_llm_model(
    llm_model_id: str | None = Query(default=None, description="LLM model ID to filter"),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """
    Retrieve LLM model(s)

    - If llm_model_id is provided, returns specific model
    - If llm_model_id is not provided, returns all models
    """

    try:
        result = await db.execute(
            text("""
                SELECT llm_model_id, llm_model_title, llm_model_keyword, ui_sort_order, description, provider, created_at, updated_at
                FROM au_system_get_llm_model(:llm_model_id)
            """),
            {
                "llm_model_id": llm_model_id,
            },
        )
        rows = result.fetchall()

        return [
            {
                "llm_model_id": row.llm_model_id,
                "llm_model_title": row.llm_model_title,
                "llm_model_keyword": row.llm_model_keyword,
                "ui_sort_order": row.ui_sort_order,
                "description": row.description,
                "provider": row.provider,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            }
            for row in rows
        ]

    except Exception as e:
        logger.error(f"Failed to retrieve LLM model: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve LLM model.",
        )


@router.put(
    "/{llm_model_id}",
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "LLM model updated"},
        404: {"description": "LLM model not found"},
        500: {"description": "Internal server error"},
    },
)
async def update_llm_model(
    llm_model_id: str,
    model_data: SystemLlmModelUpdate,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Update LLM model
    """

    try:
        result = await db.execute(
            text("""
                SELECT status, message
                FROM au_system_update_llm_model(:llm_model_id, :llm_model_title, :llm_model_keyword, :ui_sort_order, :description, :provider)
            """),
            {
                "llm_model_id": llm_model_id,
                "llm_model_title": model_data.llm_model_title,
                "llm_model_keyword": model_data.llm_model_keyword,
                "ui_sort_order": model_data.ui_sort_order,
                "description": model_data.description,
                "provider": model_data.provider,
            },
        )
        row = result.fetchone()
        await db.commit()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update LLM model",
            )

        # Set HTTP response status code from SQL function result
        response.status_code = row.status

        if row.status == 404:
            logger.info(f"pg-function: au_system_update_llm_model() - status={row.status}, message={row.message}")

        return {"status": row.status, "message": row.message}

    except HTTPException:
        await db.rollback()
        raise

    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to update LLM model: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update LLM model.",
        )


@router.delete(
    "/{llm_model_id}",
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "LLM model deleted"},
        404: {"description": "LLM model not found"},
        500: {"description": "Internal server error"},
    },
)
async def delete_llm_model(
    llm_model_id: str,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Delete LLM model (soft delete)
    """

    try:
        result = await db.execute(
            text("""
                SELECT status, message
                FROM au_system_delete_llm_model(:llm_model_id)
            """),
            {"llm_model_id": llm_model_id},
        )
        row = result.fetchone()
        await db.commit()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete LLM model",
            )

        # Set HTTP response status code from SQL function result
        response.status_code = row.status

        if row.status == 404:
            logger.info(f"pg-function: au_system_delete_llm_model() - status={row.status}, message={row.message}")

        return {"status": row.status, "message": row.message}

    except HTTPException:
        await db.rollback()
        raise

    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to delete LLM model: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete LLM model.",
        )
