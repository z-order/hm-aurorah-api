"""
Shared helper functions for file task endpoints
"""

import logging
import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionMaker
from app.core.logger import get_logger

logger = get_logger(__name__, logging.DEBUG)


async def update_file_node_status(
    file_id: uuid.UUID,
    file_status: str,
    file_message: str,
    db: AsyncSession | None = None,
) -> None:
    """Update au_file_nodes.status and message via au_update_file().

    Args:
        db: Existing session (endpoint context). If None, creates a new session (background task context).
    """
    try:
        if db is not None:
            await db.execute(
                text("""
                    SELECT status, message
                    FROM au_update_file(:file_id, NULL, NULL, :status, :message)
                """),
                {"file_id": file_id, "status": file_status, "message": file_message},
            )
            await db.commit()
        else:
            async with AsyncSessionMaker() as new_db:
                await new_db.execute(
                    text("""
                        SELECT status, message
                        FROM au_update_file(:file_id, NULL, NULL, :status, :message)
                    """),
                    {"file_id": file_id, "status": file_status, "message": file_message},
                )
                await new_db.commit()
    except Exception as e:
        if db is not None:
            await db.rollback()
        logger.error(f"Failed to update file node status: {e}")
