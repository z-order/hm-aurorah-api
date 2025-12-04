"""
AI Chatbot endpoints
"""

import logging
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import desc, select, text
from sqlalchemy.engine.result import Result
from sqlalchemy.engine.row import Row
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logger import get_logger
from app.models.chatbot_message import (
    ChatbotMessage,
    ChatbotMessageCreate,
    ChatbotMessageCreateResponse,
    ChatbotMessageRead,
    ChatbotMessageStatus,
    ChatbotMessageUpdate,
)
from app.models.chatbot_task import (
    ChatbotTask,
    ChatbotTaskCreate,
    ChatbotTaskCreateResponse,
    ChatbotTaskRead,
    ChatbotTaskStatus,
    ChatbotTaskUpdate,
)
from app.services.langgraph_client import AssistantID, langgraph_client

from .chatbot_message_c_action import atask_for_create_chatbot_message

logger = get_logger(__name__, logging.INFO)

router: APIRouter = APIRouter()

#
# CRUD for Chatbot-Tasks
#


@router.post("/task", response_model=ChatbotTaskCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_chatbot_task(
    chatbot_task_data: ChatbotTaskCreate,
    db: AsyncSession = Depends(get_db),
) -> ChatbotTask:
    """
    Create new chatbot task
    """

    try:
        # Check if user exists and get user details
        result: Result[Any] = await db.execute(
            text("SELECT * FROM auth.users WHERE id = :id"),
            {"id": chatbot_task_data.user_id},
        )
        user: Row[Any] | None = result.fetchone()
        if not user:
            logger.info(f"User not found: {chatbot_task_data.user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        # Create chatbot task
        chatbot_task: ChatbotTask = ChatbotTask(
            **chatbot_task_data.model_dump(),
            name=user.name,
            email=user.email,
            thread_id=await langgraph_client.create_thread(),
        )

        # Add chatbot task to database
        db.add(chatbot_task)
        await db.commit()
        await db.refresh(chatbot_task)  # db.refre
        return chatbot_task

    except HTTPException:
        await db.rollback()
        raise

    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create chatbot task: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create chatbot task.",
        )


@router.get("/task/{user_id}", response_model=list[ChatbotTaskRead])
async def get_chatbot_tasks(
    user_id: str,
    skip: int = Query(default=0, ge=0, description="Number of chatbot tasks to skip"),
    limit: int = Query(default=100, ge=1, le=1000, description="Number of chatbot tasks to return"),
    db: AsyncSession = Depends(get_db),
) -> Sequence[ChatbotTask]:
    """
    Retrieve all chatbot tasks
    """

    try:
        result = await db.execute(
            select(ChatbotTask)
            .where(
                ChatbotTask.user_id == user_id,  # type: ignore[arg-type]
                ChatbotTask.is_deleted.is_(False),  # type: ignore[arg-type]
            )
            .order_by(desc(ChatbotTask.updated_at))  # type: ignore[arg-type]
            .offset(skip)
            .limit(limit)
        )
        chatbot_tasks = result.scalars().all()
        return chatbot_tasks

    except Exception as e:
        logger.error(f"Failed to retrieve chatbot tasks: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve chatbot tasks.",
        )


@router.put("/task/{task_id}", response_model=ChatbotTaskRead)
async def update_chatbot_task(
    task_id: str,
    chatbot_task_data: ChatbotTaskUpdate,
    db: AsyncSession = Depends(get_db),
) -> ChatbotTask:
    """
    Update chatbot task
    """

    try:
        result = await db.execute(
            select(ChatbotTask).where(ChatbotTask.task_id == task_id)  # type: ignore[arg-type]
        )
        chatbot_task = result.scalar_one_or_none()

        if not chatbot_task:
            logger.info(f"Chatbot task not found: {task_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chatbot task not found",
            )

        # Update chatbot task fields
        update_data = chatbot_task_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(chatbot_task, field, value)

        chatbot_task.updated_at = datetime.now(UTC)

        await db.commit()
        await db.refresh(chatbot_task)
        return chatbot_task

    except HTTPException:
        await db.rollback()
        raise

    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to update chatbot task: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update chatbot task.",
        )


@router.delete("/task/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chatbot_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Delete chatbot task (soft delete)
    """

    try:
        result = await db.execute(
            select(ChatbotTask).where(ChatbotTask.task_id == task_id)  # type: ignore[arg-type]
        )
        chatbot_task = result.scalar_one_or_none()

        if not chatbot_task:
            logger.info(f"Chatbot task not found: {task_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chatbot task not found",
            )

        # Soft delete: set is_deleted to True and deleted_at timestamp
        chatbot_task.is_deleted = True
        chatbot_task.deleted_at = datetime.now(UTC)
        chatbot_task.updated_at = datetime.now(UTC)

        await db.commit()

        return None

    except HTTPException:
        await db.rollback()
        raise

    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to delete chatbot task: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete chatbot task.",
        )


#
# CRUD for Chatbot-Messages
#


@router.post("/message", response_model=ChatbotMessageCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_chatbot_message(
    background_tasks: BackgroundTasks,
    chatbot_message_data: ChatbotMessageCreate,
    db: AsyncSession = Depends(get_db),
) -> ChatbotMessage:
    """
    Create new chatbot message
    """

    try:
        # Check if user exists
        result: Result[Any] = await db.execute(
            text("SELECT * FROM auth.users WHERE id = :id"),
            {"id": chatbot_message_data.user_id},
        )
        user: Row[Any] | None = result.fetchone()
        if not user:
            logger.info(f"User not found: {chatbot_message_data.user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        # Check if task exists
        task_result = await db.execute(
            select(ChatbotTask).where(ChatbotTask.task_id == chatbot_message_data.task_id)  # type: ignore[arg-type]
        )
        task = task_result.scalar_one_or_none()
        if not task:
            logger.info(f"Chatbot task not found: {chatbot_message_data.task_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chatbot task not found",
            )

        #
        # Check if the task is running an action
        #

        # If the task is in progress, return an error.
        if task.status == ChatbotTaskStatus.IN_PROGRESS:
            # TODO: The user can cancel the task, and/or the user can check last_run_id to get the action result.
            logger.info(f"Chatbot task is already running an action: {chatbot_message_data.task_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Chatbot task is already running an action",
            )

        # If the task is ready/hitl/completed/failed/cancelled/abandoned, start the action.
        if task.status not in [
            ChatbotTaskStatus.READY,
            ChatbotTaskStatus.HITL,
            ChatbotTaskStatus.COMPLETED,
            ChatbotTaskStatus.FAILED,
            ChatbotTaskStatus.CANCELLED,
            ChatbotTaskStatus.ABANDONED,
        ]:
            logger.info(f"Chatbot task is not in a valid state: {chatbot_message_data.task_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Chatbot task is not in a valid state",
            )

        chatbot_message: ChatbotMessage | None = None

        # Create chatbot message
        if not chatbot_message_data.hitl_mode:
            # Create a new chatbot message in normal mode
            chatbot_message = ChatbotMessage(
                user_id=chatbot_message_data.user_id,
                task_id=chatbot_message_data.task_id,
                contents=[],  # TODO: Fill out these list items in the atask_for_create_chatbot_message() task
            )

            # Set the message status to pending
            chatbot_message.status = ChatbotMessageStatus.PROCESSING

            # Set the task status to in progress
            task.status = ChatbotTaskStatus.IN_PROGRESS

            # Add chatbot message to database
            db.add(chatbot_message)
            await db.commit()
            await db.refresh(chatbot_message)

            # Problem: asyncio.create_task() creates a "fire-and-forget" task,
            # but when the FastAPI request handler completes and returns the response,
            # the event loop context for that request is cleaned up.
            # The background task loses its execution context, causing the Redis async timeout to fail.
            #
            # 1. asyncio.create_task() creates a task that runs in the background
            # 2. The HTTP request returns 201 Created before the task completes
            # 3. When the request handler exits, the task gets cancelled/garbage collected
            # 4. Redis async operations fail with RuntimeError: Timeout should be used inside a task because the task context is gone
            #
            # Create a task to create the chatbot message
            # asyncio.create_task(
            #     atask_for_create_chatbot_message(
            #         task=task,
            #         chatbot_message_data=chatbot_message_data,
            #         chatbot_message=chatbot_message,
            #         assistant_id=AssistantID.TASK_TRANSLATION,
            #     )
            # )
            #
            # Solution: Use FastAPI's BackgroundTasks - pass async function directly
            background_tasks.add_task(
                atask_for_create_chatbot_message,
                task=task,
                chatbot_message_data=chatbot_message_data,
                chatbot_message=chatbot_message,
                assistant_id=AssistantID.TASK_TRANSLATION,
            )

        else:
            # HITL mode: Read existing chatbot message from database
            if not chatbot_message_data.hitl_message_id:
                logger.info(f"hitl_message_id is required in HITL mode: {chatbot_message_data.task_id}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="hitl_message_id is required in HITL mode",
                )

            message_result = await db.execute(
                select(ChatbotMessage).where(
                    ChatbotMessage.message_id == chatbot_message_data.hitl_message_id  # type: ignore[arg-type]
                )
            )
            chatbot_message = message_result.scalar_one_or_none()

            if not chatbot_message:
                logger.info(f"Chatbot message not found: {chatbot_message_data.hitl_message_id}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Chatbot message not found",
                )

            # Validate the message is in HITL status
            if chatbot_message.status != ChatbotMessageStatus.HITL:
                logger.info(f"Chatbot message is not in HITL status: {chatbot_message_data.hitl_message_id}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Chatbot message is not in HITL status",
                )

            # Set the message status to pending
            chatbot_message.status = ChatbotMessageStatus.PROCESSING

            # Set the task status to in progress
            task.status = ChatbotTaskStatus.IN_PROGRESS

            logger.info(f"chatbot_message[1]: {chatbot_message}")

            await db.commit()
            await db.refresh(chatbot_message)

            logger.info(f"chatbot_message[2]: {chatbot_message}")

            # Problem: asyncio.create_task() creates a "fire-and-forget" task,
            # but when the FastAPI request handler completes and returns the response,
            # the event loop context for that request is cleaned up.
            # The background task loses its execution context, causing the Redis async timeout to fail.
            #
            # 1. asyncio.create_task() creates a task that runs in the background
            # 2. The HTTP request returns 201 Created before the task completes
            # 3. When the request handler exits, the task gets cancelled/garbage collected
            # 4. Redis async operations fail with RuntimeError: Timeout should be used inside a task because the task context is gone
            #
            # Create a task to resume the chatbot message
            # asyncio.create_task(
            #     atask_for_create_chatbot_message(
            #         task=task,
            #         chatbot_message_data=chatbot_message_data,
            #         chatbot_message=chatbot_message,
            #         assistant_id=AssistantID.TASK_TRANSLATION,
            #         hitl_mode=True,
            #     )
            #
            # Solution: Use FastAPI's BackgroundTasks - pass async function directly
            background_tasks.add_task(
                atask_for_create_chatbot_message,
                task=task,
                chatbot_message_data=chatbot_message_data,
                chatbot_message=chatbot_message,
                assistant_id=AssistantID.TASK_TRANSLATION,
                hitl_mode=True,
            )

        # I think it will be better to use chatbot_message.message_id as a channel id for the message queue.
        # So, the Redis key of the message queue will be:
        # mq:channel:<channel_id> -> mq:channel:<chatbot_message.message_id>
        #
        # Therefore, the client can access the message queue for checking the message status by:
        #   '/api/v1/mq/channels/<chatbot_message.message_id>/events'
        # Which is the described path of the '/api/v1/mq/channels/<channel_id>/events' endpoint.

        return chatbot_message

    except HTTPException:
        await db.rollback()
        raise

    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create chatbot message: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create chatbot message.",
        )


@router.get("/message/{task_id}", response_model=list[ChatbotMessageRead])
async def get_chatbot_messages(
    task_id: str,
    skip: int = Query(default=0, ge=0, description="Number of chatbot messages to skip"),
    limit: int = Query(default=100, ge=1, le=1000, description="Number of chatbot messages to return"),
    db: AsyncSession = Depends(get_db),
) -> Sequence[ChatbotMessage]:
    """
    Retrieve all chatbot messages
    """

    try:
        result = await db.execute(
            select(ChatbotMessage)
            .where(
                ChatbotMessage.task_id == task_id,  # type: ignore[arg-type]
                ChatbotMessage.is_deleted.is_(False),  # type: ignore[arg-type]
            )
            .order_by(desc(ChatbotMessage.updated_at))  # type: ignore[arg-type]
            .offset(skip)
            .limit(limit)
        )
        chatbot_messages = result.scalars().all()
        return chatbot_messages

    except Exception as e:
        logger.error(f"Failed to retrieve chatbot messages: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve chatbot messages.",
        )


@router.put("/message/{message_id}", response_model=ChatbotMessageRead)
async def update_chatbot_message(
    message_id: str,
    chatbot_message_data: ChatbotMessageUpdate,
    db: AsyncSession = Depends(get_db),
) -> ChatbotMessage:
    """
    Update chatbot message
    """

    try:
        result = await db.execute(
            select(ChatbotMessage).where(ChatbotMessage.message_id == message_id)  # type: ignore[arg-type]
        )
        chatbot_message = result.scalar_one_or_none()

        if not chatbot_message:
            logger.info(f"Chatbot message not found: {message_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chatbot message not found",
            )

        # Update chatbot message fields
        # NOTE: ChatbotMessageUpdate has content and files fields,
        # but ChatbotMessage model has contents (list of ChatbotMessageContent).
        # This requires transformation logic to update the contents list properly.
        # TODO: Implement the conversion from ChatbotMessageUpdate to ChatbotMessage.contents
        # For now, using model_dump to update fields that exist in both schemas.
        update_data = chatbot_message_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(chatbot_message, field):
                setattr(chatbot_message, field, value)

        chatbot_message.updated_at = datetime.now(UTC)

        await db.commit()
        await db.refresh(chatbot_message)
        return chatbot_message

    except HTTPException:
        await db.rollback()
        raise

    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to update chatbot message: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update chatbot message.",
        )


@router.delete("/message/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chatbot_message(
    message_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Delete chatbot message (soft delete)
    """

    try:
        result = await db.execute(
            select(ChatbotMessage).where(ChatbotMessage.message_id == message_id)  # type: ignore[arg-type]
        )
        chatbot_message = result.scalar_one_or_none()

        if not chatbot_message:
            logger.info(f"Chatbot message not found: {message_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chatbot message not found",
            )

        # Soft delete: set is_deleted to True and deleted_at timestamp
        chatbot_message.is_deleted = True
        chatbot_message.deleted_at = datetime.now(UTC)
        chatbot_message.updated_at = datetime.now(UTC)

        await db.commit()

        return None

    except HTTPException:
        await db.rollback()
        raise

    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to delete chatbot message: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete chatbot message.",
        )
