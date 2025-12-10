"""
Chatbot message create action
"""

import logging
from datetime import UTC, datetime
from typing import Any, Literal, cast

import httpx
from sqlalchemy import update

from app.core.config import settings
from app.core.database import AsyncSessionMaker
from app.core.logger import get_logger
from app.core.rsmqueue import RedisStreamMessageQueue
from app.models.chatbot_message import ChatbotMessage, ChatbotMessageCreate, ChatbotMessageStatus
from app.models.chatbot_task import ChatbotTask, ChatbotTaskStatus
from app.services.langgraph_client import AssistantID, langgraph_client

logger = get_logger(__name__, logging.DEBUG)


async def atask_for_create_chatbot_message(
    task: ChatbotTask,
    chatbot_message_data: ChatbotMessageCreate,
    chatbot_message: ChatbotMessage,
    *,
    assistant_id: AssistantID,
    hitl_mode: bool = False,
) -> None:
    """
    Async task for creating a chatbot message
    """

    try:
        # Initialize the message queue.
        mq = RedisStreamMessageQueue(
            ttl_seconds=settings.REDIS_STREAM_MQ_TTL_SECONDS,
            maxlen=settings.REDIS_STREAM_MQ_MAXLEN,
        )

        # Set the variables.
        user_id: str = task.user_id
        task_id: str = cast(str, task.task_id)
        thread_id: str = (
            # If the assistant is the AssistantID.TASK_ASSISTANT, use the thread_id from the task.
            # If hitl_mode is True, use the thread_id from the chatbot_message.thread_id
            # If hitl_mode is False, create a new thread for the new task.
            task.thread_id
            if assistant_id == AssistantID.TASK_ASSISTANT
            else cast(str, chatbot_message.thread_id)
            if hitl_mode
            else await langgraph_client.create_thread()
        )
        prompt: str = chatbot_message_data.content

        # Update the chatbot message thread_id to database.
        async with AsyncSessionMaker() as db:
            await db.execute(
                update(ChatbotMessage)
                .where(ChatbotMessage.message_id == chatbot_message.message_id)  # type: ignore[arg-type]
                .values(thread_id=thread_id, updated_at=datetime.now(UTC))
            )
            await db.commit()
        chatbot_message.thread_id = thread_id  # Update local object for later use

        #####################
        # Process the files #
        ##################### ---->> Start
        # chatbot_message_data.files will be processed here.
        for file in chatbot_message_data.files:
            # check if the file is .txt extension, if not, skip it.
            if file.extension != "txt":
                continue

            # Read the file content from the file.url
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(file.url)
                    response.raise_for_status()
                    file_content = response.text
            except Exception as e:
                logger.error(f"Failed to read file from {file.url}: {str(e)}")
                continue

            # Add the file content to the prompt
            prompt = f"\n\n{file_content}"
        ##################### <<---- End

        # Set async generator for handling .run_new_task() and/or .run_hitl_task()
        async_generator = (
            langgraph_client.run_new_task(user_id, task_id, thread_id, assistant_id, prompt)
            if not hitl_mode
            else langgraph_client.run_hitl_task(user_id, task_id, thread_id, assistant_id, prompt)
        )

        # Flag to check if the stream was interrupted (HITL)
        is_interrupted: bool = False
        last_message_type: Literal["ai", "tool", "unknown"] = "unknown"

        # chatbot_message_data.content will be processed here.
        async for chunk in async_generator:
            # Parse the chunk
            parsed_chunk = await langgraph_client.parse_chunk(user_id, task_id, thread_id, chunk)

            # If necessary, refine the chunk before sending it to the client via SSE
            # ...

            # If the chunk is a metadata, tasks, or updates event, send it to the client via SSE
            if parsed_chunk and parsed_chunk["event"] in ["metadata", "tasks", "updates"]:
                # Prepare the payload for the langgraph stream chunk
                payload = {
                    "type": chunk.event,
                    "data": cast(dict[str, Any], chunk.data),
                }

                # Send the langgraph stream chunk to the client via SSE
                await mq.broadcast(cast(str, chatbot_message.message_id), "langgraph_stream_chunk", payload)
                logger.debug(f"LangGraph stream chunk broadcasted to channel: {chatbot_message.message_id}")

            # Process the events chunk
            elif parsed_chunk and parsed_chunk["event"] == "events":
                # Start of the stream message
                if parsed_chunk["event_name"] == "on_chat_model_start":
                    pass
                elif parsed_chunk["event_name"] == "on_chat_model_stream":
                    last_message_type = (
                        "ai" if parsed_chunk["is_ai_message"] else "tool" if parsed_chunk["is_tool_call"] else "unknown"
                    )
                    # Send the stream message chunk to the client via SSE
                    await mq.broadcast(
                        cast(str, chatbot_message.message_id),
                        "model_stream_chunk",
                        {
                            "type": last_message_type,
                            "message": parsed_chunk["chunk_data"],
                            "status": ChatbotMessageStatus.PROCESSING,
                        },
                    )

                # End of the stream message
                elif parsed_chunk["event_name"] == "on_chat_model_end":
                    # Send the final stream message chunk to the client via SSE
                    await mq.broadcast(
                        cast(str, chatbot_message.message_id),
                        "model_stream_chunk",
                        {
                            "type": last_message_type,
                            "message": "",
                            "status": ChatbotMessageStatus.COMPLETED,
                        },
                    )

            # Update the last_run_id into task from metadata chunk.
            if parsed_chunk and parsed_chunk["event"] == "metadata" and parsed_chunk["run_id"]:
                run_id: str = parsed_chunk["run_id"]
                async with AsyncSessionMaker() as db:
                    await db.execute(
                        update(ChatbotTask)
                        .where(ChatbotTask.task_id == task.task_id)  # type: ignore[arg-type]
                        .values(last_run_id=run_id, updated_at=datetime.now(UTC))
                    )
                    await db.commit()
                logger.info(f"User: {user_id}, Task: {task_id}, Thread: {thread_id}, last_run_id updated: {run_id}")

            # Check if the langgraph stream chunk is an interrupt event for Human-in-the-loop (HITL)
            if parsed_chunk and parsed_chunk["event"] == "tasks" and parsed_chunk["is_interrupted"]:
                interrupt_msg: str = parsed_chunk["interrupt_msg"] if parsed_chunk["interrupt_msg"] else ""
                await mq.broadcast(
                    cast(str, chatbot_message.message_id),
                    "ai_message",
                    {
                        "type": "ai",
                        "message": interrupt_msg,
                        "status": ChatbotMessageStatus.HITL,
                        "message_id": chatbot_message.message_id,
                    },
                )
                logger.debug(f"AI message broadcasted to channel: {chatbot_message.message_id}")

                # Set the is_interrupted flag to True to update the chatbot message and task status to HITL in the below block.
                is_interrupted = True

        if is_interrupted:
            # Update the chatbot message and task status to HITL
            async with AsyncSessionMaker() as db:
                # Update the chatbot message status to HITL
                await db.execute(
                    update(ChatbotMessage)
                    .where(ChatbotMessage.message_id == chatbot_message.message_id)  # type: ignore[arg-type]
                    .values(status=ChatbotMessageStatus.HITL, updated_at=datetime.now(UTC))
                )

                # Update the task status to HITL
                await db.execute(
                    update(ChatbotTask)
                    .where(ChatbotTask.task_id == task.task_id)  # type: ignore[arg-type]
                    .values(status=ChatbotTaskStatus.HITL, updated_at=datetime.now(UTC))
                )

                # Commit the changes to the database
                await db.commit()
        else:
            # Update the chatbot message and task status to completed
            async with AsyncSessionMaker() as db:
                # Update the chatbot message status to completed
                await db.execute(
                    update(ChatbotMessage)
                    .where(ChatbotMessage.message_id == chatbot_message.message_id)  # type: ignore[arg-type]
                    .values(status=ChatbotMessageStatus.COMPLETED, updated_at=datetime.now(UTC))
                )

                # Update the task status to completed
                await db.execute(
                    update(ChatbotTask)
                    .where(ChatbotTask.task_id == task.task_id)  # type: ignore[arg-type]
                    .values(status=ChatbotTaskStatus.COMPLETED, updated_at=datetime.now(UTC))
                )

                # Commit the changes to the database
                await db.commit()

            # Update the message queue to mark the message as done
            await mq.send(cast(str, chatbot_message.message_id), {"type": "done"})
            logger.debug(f"System message sent to channel: {chatbot_message.message_id} marked as done")

    except Exception as e:
        logger.error(
            f"Failed to create chatbot message: {str(e)}",
            exc_info=True,
        )

        # Update the chatbot message and task status to failed
        async with AsyncSessionMaker() as db:
            # Update the chatbot message status to failed
            await db.execute(
                update(ChatbotMessage)
                .where(ChatbotMessage.message_id == chatbot_message.message_id)  # type: ignore[arg-type]
                .values(status=ChatbotMessageStatus.FAILED, updated_at=datetime.now(UTC))
            )

            # Update the task status to failed
            await db.execute(
                update(ChatbotTask)
                .where(ChatbotTask.task_id == task.task_id)  # type: ignore[arg-type]
                .values(status=ChatbotTaskStatus.FAILED, updated_at=datetime.now(UTC))
            )

            # Commit the changes to the database
            await db.commit()
