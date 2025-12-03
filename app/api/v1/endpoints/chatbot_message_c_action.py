"""
Chatbot message create action
"""

import logging
from datetime import UTC, datetime
from typing import Any, cast

from sqlalchemy import update

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
        mq = RedisStreamMessageQueue()

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

        # chatbot_message_data.files will be processed here.
        # ...

        # Set async generator for handling .run_new_task() and/or .run_hitl_task()
        async_generator = (
            langgraph_client.run_new_task(user_id, task_id, thread_id, assistant_id, prompt)
            if not hitl_mode
            else langgraph_client.run_hitl_task(user_id, task_id, thread_id, assistant_id, prompt)
        )

        # chatbot_message_data.content will be processed here.
        async for chunk in async_generator:
            # Log the langgraph stream chunk
            logger.debug(f"User: {user_id}, Task: {task_id}, Thread: {thread_id}, LangGraph stream chunk: {chunk}")

            # If necessary, refine the chunk before sending it to the client via SSE
            # ...

            # Prepare the payload for the langgraph stream chunk
            payload = {
                "event": chunk.event,
                "data": cast(dict[str, Any], chunk.data),
            }

            # Send the langgraph stream chunk to the client via SSE
            await mq.broadcast(cast(str, chatbot_message.message_id), "langgraph_stream_chunk", payload)
            logger.debug(f"LangGraph stream chunk broadcasted to channel: {chatbot_message.message_id}")

            # If chunk includes StreamPart(event='metadata', data={'run_id': '...'}), update last_run_id into task.
            if chunk.event == "metadata" and isinstance(chunk.data, dict) and "run_id" in chunk.data:  # type: ignore[arg-type]
                run_id: str = cast(str, chunk.data["run_id"])
                async with AsyncSessionMaker() as db:
                    await db.execute(
                        update(ChatbotTask)
                        .where(ChatbotTask.task_id == task.task_id)  # type: ignore[arg-type]
                        .values(last_run_id=run_id, updated_at=datetime.now(UTC))
                    )
                    await db.commit()
                logger.info(f"User: {user_id}, Task: {task_id}, Thread: {thread_id}, last_run_id updated: {run_id}")

            # Check if the langgraph stream chunk is an interrupt event for Human-in-the-loop (HITL)
            # --------------------------------------------------------------------------------------
            # Example of the interrupt event:
            # StreamPart(event="values", data={
            #     "__interrupt__": [{
            #         "value": {
            #             "call_chain": ["ask_user_for_clarifying_task", "__human_in_the_loop", "interrupt"],
            #             "next_node": "check_analyzed_result_by_llm",
            #             "cause": "ASKU found",
            #             "msg": "..."
            #         },
            #         "id": "..."
            #     }]
            # })
            if chunk.event == "values" and isinstance(chunk.data, dict) and "__interrupt__" in chunk.data:  # type: ignore[arg-type]
                interrupt_data = cast(list[dict[str, Any]], chunk.data["__interrupt__"])
                if len(interrupt_data) > 0 and "value" in interrupt_data[0] and "msg" in interrupt_data[0]["value"]:
                    interrupt_msg: str = interrupt_data[0]["value"]["msg"]
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

                # TEST: Send a human message to the AI agent to clarify the AI's questions.
                # chatbot_message_data.content = "Target language is Korean, country is South Korea, audience is adults, purpose is web novel translation"
                # await atask_for_create_chatbot_message(
                #     task=task,
                #     chatbot_message_data=chatbot_message_data,
                #     chatbot_message=chatbot_message,
                #     assistant_id=assistant_id,
                #     hitl_mode=True,
                # )

                # Return here, and wait for the human input in the next message.
                return

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
        #
        # For testing... block done message sending here.
        #
        # await mq.send(cast(str, chatbot_message.message_id), {"type": "done"})
        # logger.debug(f"System message sent to channel: {chatbot_message.message_id} marked as done")
        #

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
