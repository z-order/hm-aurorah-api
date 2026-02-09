"""
File translation task

This module handles the background task for file translation using LangGraph AI Agent.

Flow:
1. Get file preset from database (translation settings)
2. Get original text from database (source text to translate)
3. Build translation prompt with preset settings
4. Call LangGraph AI Agent for translation
5. Collect and format translated chunks
6. Update database with translated text and status
"""

import asyncio
import json
import logging
import uuid
from typing import Any

from sqlalchemy import text

from app.core.config import settings
from app.core.database import AsyncSessionMaker
from app.core.logger import get_logger
from app.core.rsmqueue import RedisStreamMessageQueue
from app.models.file_translation import FileTranslationCreate
from app.services.langgraph_chunk_processor import get_langgraph_chunk_collector, process_langgraph_chunk
from app.services.langgraph_client import AssistantID, langgraph_client

logger = get_logger(__name__, logging.DEBUG)


# =============================================================================
# MAIN BACKGROUND TASK FUNCTION
# =============================================================================


async def bg_atask_create_file_translation(
    rsmq_channel_id: str,
    translation_id: uuid.UUID,
    translation_data: FileTranslationCreate,
    ready_event: asyncio.Event | None = None,
) -> None:
    """
    Async background task for creating a file translation using LangGraph AI Agent.

    Args:
        rsmq_channel_id: Redis Stream Message Queue channel ID for real-time streaming
        translation_id: The translation record ID in database
        translation_data: Translation request data containing file_id, preset_id, assignee_id
        ready_event: Optional event to signal when task is ready for streaming
    """

    # -------------------------------------------------------------------------
    # STEP 1: Initialize variables and connections
    # -------------------------------------------------------------------------
    try:
        # Initialize the Redis Stream Message Queue for real-time client updates
        mq = RedisStreamMessageQueue(
            ttl_seconds=settings.REDIS_STREAM_MQ_TTL_SECONDS,
            maxlen=settings.REDIS_STREAM_MQ_MAXLEN,
        )

        # Create a new thread in LangGraph for this translation session
        thread_id: str = await langgraph_client.create_thread()

        # Map translation data to LangGraph identifiers
        user_id: str = str(translation_data.assignee_id)  # assignee_id as user_id
        task_id: str = str(translation_data.file_id)  # file_id as task_id
        file_id: uuid.UUID = translation_data.file_id
        file_preset_id: uuid.UUID = translation_data.file_preset_id
        principal_id: uuid.UUID = translation_data.assignee_id  # Use assignee_id as principal_id

        # Initialize variables for later use
        assistant_id: AssistantID = AssistantID.TASK_TRANSLATION_A1  # Default, will be updated from preset
        last_run_id: str = ""

        # -------------------------------------------------------------------------
        # STEP 2: Get file preset from database
        # -------------------------------------------------------------------------
        preset_data = await _get_file_preset(principal_id, file_preset_id)
        if preset_data is None:
            raise ValueError(f"File preset not found: {file_preset_id}")

        # Extract assistant_id from preset (ai_agent_id maps to AssistantID)
        ai_agent_id: str = preset_data.get("ai_agent_id", "task_translation_a1")
        assistant_id = AssistantID.from_agent_id(ai_agent_id)

        # -------------------------------------------------------------------------
        # STEP 3: Get original text from database
        # -------------------------------------------------------------------------
        original_data = await _get_original_text(file_id)
        if original_data is None:
            raise ValueError(f"Original text not found for file: {file_id}")

        original_text: dict[str, Any] = original_data.get("original_text", {})

        # -------------------------------------------------------------------------
        # STEP 4: Build translation prompt
        # -------------------------------------------------------------------------
        prompt = _build_translation_prompt(original_text)

        # Extract translation config from preset for LangGraph
        translation_memory: str | None = preset_data.get("translation_memory")
        translation_role: str | None = preset_data.get("translation_role")
        translation_rules: str | None = preset_data.get("translation_rule")
        llm_model_id: str | None = preset_data.get("llm_model_id")
        llm_model_temperature: float | None = preset_data.get("llm_model_temperature")

        # -------------------------------------------------------------------------
        # STEP 5: Update database status to "in_progress"
        # -------------------------------------------------------------------------
        ai_agent_data: dict[str, Any] = {
            "agent_id": ai_agent_id,
            "thread_id": thread_id,
            "last_run_id": "",  # Will be updated when we receive metadata
            "rsmq_channel_id": rsmq_channel_id,
        }

        await _update_translation_status(
            translation_id=translation_id,
            ai_agent_data=ai_agent_data,
            status="in_progress",
            message=None,
        )

        # -------------------------------------------------------------------------
        # STEP 6: Signal that the task is ready for streaming
        # -------------------------------------------------------------------------
        if ready_event:
            ready_event.set()

        # -------------------------------------------------------------------------
        # STEP 7: Run LangGraph AI Agent and collect chunks
        # -------------------------------------------------------------------------
        # Set async generator for handling .run_new_task()
        async_generator = langgraph_client.run_new_task(
            user_id=user_id,
            task_id=task_id,
            thread_id=thread_id,
            assistant_id=assistant_id,
            prompt=prompt,
            translation_memory=translation_memory,
            translation_role=translation_role,
            translation_rules=translation_rules,
            llm_model_id=llm_model_id,
            llm_model_temperature=llm_model_temperature,
        )

        # Initialize chunk collector based on AI agent type
        chunk_collector = get_langgraph_chunk_collector(ai_agent_id)

        # Process each chunk from the LangGraph stream
        async for chunk in async_generator:
            # Parse the chunk using LangGraph client
            parsed_chunk = await langgraph_client.parse_chunk(user_id, task_id, thread_id, chunk)

            # Process and collect the chunk
            await process_langgraph_chunk(
                mq=mq,
                channel_id=rsmq_channel_id,
                parsed_chunk=parsed_chunk,
                chunk_collector=chunk_collector,
            )

            # Update last_run_id from metadata chunk
            if parsed_chunk and parsed_chunk["event"] == "metadata" and parsed_chunk["run_id"]:
                last_run_id = parsed_chunk["run_id"]
                ai_agent_data["last_run_id"] = last_run_id

        # -------------------------------------------------------------------------
        # STEP 8: Format collected chunks into translated_text
        # -------------------------------------------------------------------------
        translated_text = chunk_collector.format_result()

        # -------------------------------------------------------------------------
        # STEP 9: Update database with completed translation
        # -------------------------------------------------------------------------
        await _update_translation_with_result(
            translation_id=translation_id,
            translated_text=translated_text,
            ai_agent_data=ai_agent_data,
            status="completed",
            message=None,
        )

        # Send completion message to client via message queue
        await mq.send(rsmq_channel_id, {"type": "done"})
        logger.info(f"Translation completed: translation_id={translation_id}")

    except ValueError as e:
        # -------------------------------------------------------------------------
        # VALIDATION ERROR (Known errors): Log message only (no stack trace)
        # -------------------------------------------------------------------------
        # Catches:
        #   - _get_file_preset() returns None   -> "File preset not found: {id}"
        #   - _get_original_text() returns None -> "Original text not found for file: {id}"
        #   - langgraph_client.run_new_task()   -> "Unsupported assistant ID: {id}"
        # -------------------------------------------------------------------------
        logger.error(f"Failed to create file translation: {str(e)}")

        try:
            await _update_translation_status(
                translation_id=translation_id,
                ai_agent_data=None,
                status="failed",
                message=str(e),
            )
        except Exception as update_error:
            logger.error(f"Failed to update translation status to failed: {update_error}")

    except Exception as e:
        # -------------------------------------------------------------------------
        # SYSTEM ERROR: Log full stack trace, save simple message to database
        # -------------------------------------------------------------------------
        # Catches:
        #   - langgraph_client.create_thread()         -> HTTPException (timeout, connection, API)
        #   - langgraph_client.run_new_task()          -> HTTPException
        #   - langgraph_client.parse_chunk()           -> HTTPException
        #   - _update_translation_status()             -> DB exceptions (SQLAlchemy)
        #   - _update_translation_with_result()        -> DB exceptions (SQLAlchemy)
        #   - mq.send() / mq.broadcast()               -> Redis connection exceptions
        # -------------------------------------------------------------------------
        logger.error(
            f"Failed to create file translation: {str(e)}",
            exc_info=True,
        )

        try:
            error_type = type(e).__name__
            await _update_translation_status(
                translation_id=translation_id,
                ai_agent_data=None,
                status="failed",
                message=f"System error ({error_type}). Check the server logs for details.",
            )
        except Exception as update_error:
            logger.error(f"Failed to update translation status to failed: {update_error}")


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


async def _get_file_preset(
    principal_id: uuid.UUID,
    file_preset_id: uuid.UUID,
) -> dict[str, Any] | None:
    """
    Get file preset from database using SQL function.

    Args:
        principal_id: The principal (user/team/group) ID who owns the preset
        file_preset_id: The preset ID to retrieve

    Returns:
        Preset data as dictionary, or None if not found
    """
    async with AsyncSessionMaker() as db:
        result = await db.execute(
            text("""
                SELECT file_preset_id, principal_id, description,
                       llm_model_id, llm_model_temperature, ai_agent_id,
                       translation_memory, translation_role, translation_rule,
                       target_language, target_country, target_city,
                       task_type, audience, purpose, created_at, updated_at
                FROM au_get_file_preset(:principal_id, :file_preset_id)
            """),
            {
                "principal_id": principal_id,
                "file_preset_id": file_preset_id,
            },
        )
        row = result.fetchone()

        if not row:
            return None

        return {
            "file_preset_id": row.file_preset_id,
            "principal_id": row.principal_id,
            "description": row.description,
            "llm_model_id": row.llm_model_id,
            "llm_model_temperature": row.llm_model_temperature,
            "ai_agent_id": row.ai_agent_id,
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


async def _get_original_text(file_id: uuid.UUID) -> dict[str, Any] | None:
    """
    Get original text from database using SQL function.

    Args:
        file_id: The file ID to get original text for

    Returns:
        Original text data as dictionary, or None if not found
    """
    async with AsyncSessionMaker() as db:
        result = await db.execute(
            text("""
                SELECT original_id, file_id, original_text, original_text_modified,
                       created_at, updated_at
                FROM au_get_file_original(:file_id, NULL)
            """),
            {"file_id": file_id},
        )
        row = result.fetchone()

        if not row:
            return None

        return {
            "original_id": row.original_id,
            "file_id": row.file_id,
            "original_text": row.original_text,
            "original_text_modified": row.original_text_modified,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }


def _build_translation_prompt(original_text: dict[str, Any]) -> str:
    """
    Build the translation prompt from original text.

    The original_text is expected to be a JSONB with segments structure:
    {
        "segments": [
            {"sid": 1, "text": "First sentence."},
            {"sid": 2, "text": "Second sentence."},
            ...
        ]
    }

    Args:
        original_text: Original text as segments dictionary

    Returns:
        Original text as JSON string for the AI agent prompt
    """
    # Return original_text as JSON string
    return json.dumps(original_text, ensure_ascii=False)


# =============================================================================
# DATABASE UPDATE FUNCTIONS
# =============================================================================


async def _update_translation_status(
    translation_id: uuid.UUID,
    ai_agent_data: dict[str, Any] | None,
    status: str,
    message: str | None,
) -> None:
    """
    Update translation status in database (ai_agent_data, status, message columns only).

    Args:
        translation_id: The translation record ID
        ai_agent_data: AI agent data to store (thread_id, run_id, etc.), or None to keep existing
        status: New status ("ready", "in_progress", "completed", "failed", "cancelled", "abandoned")
        message: Error message (for "failed" status) or None
    """
    async with AsyncSessionMaker() as db:
        result = await db.execute(
            text("""
                SELECT status, message
                FROM au_update_file_translation(
                    :translation_id,
                    NULL,
                    NULL,
                    :ai_agent_data,
                    :status,
                    :message
                )
            """),
            {
                "translation_id": translation_id,
                "ai_agent_data": json.dumps(ai_agent_data) if ai_agent_data else None,
                "status": status,
                "message": message,
            },
        )
        row = result.fetchone()
        await db.commit()

        if row and row.status != 200:
            logger.warning(f"Update translation status warning: {row.message}")


async def _update_translation_with_result(
    translation_id: uuid.UUID,
    translated_text: dict[str, Any],
    ai_agent_data: dict[str, Any],
    status: str,
    message: str | None,
) -> None:
    """
    Update translation with final result including translated_text.

    Args:
        translation_id: The translation record ID
        translated_text: The formatted translated text as dictionary
        ai_agent_data: AI agent data to store
        status: New status (typically "completed")
        message: Optional message
    """
    async with AsyncSessionMaker() as db:
        result = await db.execute(
            text("""
                SELECT status, message
                FROM au_update_file_translation(
                    :translation_id,
                    :translated_text,
                    NULL,
                    :ai_agent_data,
                    :status,
                    :message
                )
            """),
            {
                "translation_id": translation_id,
                "translated_text": json.dumps(translated_text),
                "ai_agent_data": json.dumps(ai_agent_data),
                "status": status,
                "message": message,
            },
        )
        row = result.fetchone()
        await db.commit()

        if row and row.status != 200:
            logger.warning(f"Update translation result warning: {row.message}")
