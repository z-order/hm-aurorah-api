"""
System AI agent endpoints

Endpoint                      SQL Function
----------------------------  ------------------
POST /upsert                  au_system_upsert_ai_agent()
POST /                        au_system_create_ai_agent()
GET /                         au_system_get_ai_agent()
PUT /{ai_agent_id}            au_system_update_ai_agent()
DELETE /{ai_agent_id}         au_system_delete_ai_agent()

SQL Function                  Status Codes
----------------------------  --------------------------
au_system_upsert_ai_agent     200(OK/Updated), 201(Created)
au_system_create_ai_agent     200(OK), 409(Conflict)
au_system_update_ai_agent     200(OK), 404(Not Found)
au_system_delete_ai_agent     200(OK), 404(Not Found)
au_system_get_ai_agent        (no status, returns rows)

See: scripts/schema-functions/schema-public.system.ai-agent.sql
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logger import get_logger
from app.models.system_ai_agent import (
    SystemAIAgentCreate,
    SystemAIAgentRead,
    SystemAIAgentUpdate,
    SystemAIAgentUpsert,
)

logger = get_logger(__name__, logging.INFO)

router: APIRouter = APIRouter()


@router.post(
    "/upsert",
    summary="Upsert AI Agent",
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "AI agent updated or already exists"},
        201: {"description": "AI agent created"},
        500: {"description": "Internal server error"},
    },
)
async def upsert_ai_agent(
    agent_data: SystemAIAgentUpsert,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Upsert AI agent (insert or update)

    - If agent does not exist, creates new one (returns 201)
    - If agent exists with different values, updates it (returns 200)
    - If agent exists with same values, no change (returns 200)
    - If agent was soft-deleted, resurrects it
    """

    try:
        result = await db.execute(
            text("""
                SELECT status, message
                FROM au_system_upsert_ai_agent(
                    :ai_agent_id, :ai_agent_title, :ai_agent_keyword, :ui_sort_order, :description)
            """),
            {
                "ai_agent_id": agent_data.ai_agent_id,
                "ai_agent_title": agent_data.ai_agent_title,
                "ai_agent_keyword": agent_data.ai_agent_keyword,
                "ui_sort_order": agent_data.ui_sort_order,
                "description": agent_data.description,
            },
        )
        row = result.fetchone()
        await db.commit()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upsert AI agent",
            )

        # Set HTTP response status code from SQL function result
        response.status_code = row.status

        return {"status": row.status, "message": row.message}

    except HTTPException:
        await db.rollback()
        raise

    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to upsert AI agent: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upsert AI agent.",
        )


@router.post(
    "/",
    summary="Create AI Agent",
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "AI agent created"},
        409: {"description": "AI agent already exists"},
        500: {"description": "Internal server error"},
    },
)
async def create_ai_agent(
    agent_data: SystemAIAgentCreate,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Create new AI agent
    """

    try:
        result = await db.execute(
            text("""
                SELECT status, message
                FROM au_system_create_ai_agent(
                    :ai_agent_id, :ai_agent_title, :ai_agent_keyword, :ui_sort_order, :description)
            """),
            {
                "ai_agent_id": agent_data.ai_agent_id,
                "ai_agent_title": agent_data.ai_agent_title,
                "ai_agent_keyword": agent_data.ai_agent_keyword,
                "ui_sort_order": agent_data.ui_sort_order,
                "description": agent_data.description,
            },
        )
        row = result.fetchone()
        await db.commit()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create AI agent",
            )

        # Set HTTP response status code from SQL function result
        response.status_code = row.status

        if row.status == 409:
            logger.info(f"pg-function: au_system_create_ai_agent() - status={row.status}, message={row.message}")

        return {"status": row.status, "message": row.message}

    except HTTPException:
        await db.rollback()
        raise

    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create AI agent: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create AI agent.",
        )


@router.get(
    "/",
    summary="Get AI Agent",
    response_model=list[SystemAIAgentRead],
    responses={
        500: {"description": "Internal server error"},
    },
)
async def get_ai_agent(
    ai_agent_id: str | None = Query(default=None, description="AI agent ID to filter"),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """
    Retrieve AI agent(s)

    - If ai_agent_id is provided, returns specific agent
    - If ai_agent_id is not provided, returns all agents
    """

    try:
        result = await db.execute(
            text("""
                SELECT ai_agent_id, ai_agent_title, ai_agent_keyword, ui_sort_order, description, created_at, updated_at
                FROM au_system_get_ai_agent(:ai_agent_id)
            """),
            {
                "ai_agent_id": ai_agent_id,
            },
        )
        rows = result.fetchall()

        return [
            {
                "ai_agent_id": row.ai_agent_id,
                "ai_agent_title": row.ai_agent_title,
                "ai_agent_keyword": row.ai_agent_keyword,
                "ui_sort_order": row.ui_sort_order,
                "description": row.description,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            }
            for row in rows
        ]

    except Exception as e:
        logger.error(f"Failed to retrieve AI agent: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve AI agent.",
        )


@router.put(
    "/{ai_agent_id}",
    summary="Update AI Agent",
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "AI agent updated"},
        404: {"description": "AI agent not found"},
        500: {"description": "Internal server error"},
    },
)
async def update_ai_agent(
    ai_agent_id: str,
    agent_data: SystemAIAgentUpdate,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Update AI agent
    """

    try:
        result = await db.execute(
            text("""
                SELECT status, message
                FROM au_system_update_ai_agent(
                    :ai_agent_id, :ai_agent_title, :ai_agent_keyword, :ui_sort_order, :description)
            """),
            {
                "ai_agent_id": ai_agent_id,
                "ai_agent_title": agent_data.ai_agent_title,
                "ai_agent_keyword": agent_data.ai_agent_keyword,
                "ui_sort_order": agent_data.ui_sort_order,
                "description": agent_data.description,
            },
        )
        row = result.fetchone()
        await db.commit()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update AI agent",
            )

        # Set HTTP response status code from SQL function result
        response.status_code = row.status

        if row.status == 404:
            logger.info(f"pg-function: au_system_update_ai_agent() - status={row.status}, message={row.message}")

        return {"status": row.status, "message": row.message}

    except HTTPException:
        await db.rollback()
        raise

    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to update AI agent: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update AI agent.",
        )


@router.delete(
    "/{ai_agent_id}",
    summary="Delete AI Agent",
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "AI agent deleted"},
        404: {"description": "AI agent not found"},
        500: {"description": "Internal server error"},
    },
)
async def delete_ai_agent(
    ai_agent_id: str,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Delete AI agent (soft delete)
    """

    try:
        result = await db.execute(
            text("""
                SELECT status, message
                FROM au_system_delete_ai_agent(:ai_agent_id)
            """),
            {"ai_agent_id": ai_agent_id},
        )
        row = result.fetchone()
        await db.commit()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete AI agent",
            )

        # Set HTTP response status code from SQL function result
        response.status_code = row.status

        if row.status == 404:
            logger.info(f"pg-function: au_system_delete_ai_agent() - status={row.status}, message={row.message}")

        return {"status": row.status, "message": row.message}

    except HTTPException:
        await db.rollback()
        raise

    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to delete AI agent: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete AI agent.",
        )
