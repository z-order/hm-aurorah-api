"""
LangGraph AI Agent Service Client

Integration with hm-aurorah-lang (LangGraph/LangChain service)

StreamMode Reference:
---------------------
1. "values" - Full State Snapshots
   Returns the complete state after each node execution.
   Example: {"messages": [...all messages...], "context": {...full context...}}
   Use when you need the entire current state at each step.

2. "messages" - AI Message Streaming
   Streams individual message chunks as the LLM generates them.
   Example: "Hello" -> " world" -> "!" (token by token)
   Use for real-time chat UI where you show typing effect.

3. "updates" - Delta Changes Only
   Returns only what changed in each step, not the full state.
   Example: {"node_name": {"new_field": "added_value"}}
   Use when you only care about incremental changes.

4. "events" - Execution Events
   Streams lifecycle events (on_chain_start, on_llm_end, etc.).
   Example: {"event": "on_llm_start", "name": "ChatOpenAI", ...}
   Use for detailed monitoring/logging of graph execution.

5. "tasks" - Task Lifecycle
   Streams when tasks start and finish.
   Example: {"task_id": "abc", "status": "started"} -> {"task_id": "abc", "status": "finished"}
   Use for tracking parallel task execution.

6. "checkpoints" - State Persistence Points
   Streams checkpoint data as graph saves state.
   Example: {"checkpoint_id": "123", "state": {...}}
   Use for debugging state persistence or implementing time-travel.

7. "debug" - Verbose Debug Info
   Streams detailed internal execution information.
   Example: {"type": "task", "payload": {...detailed internals...}}
   Use for troubleshooting graph behavior.

8. "custom" - User-Defined Events
   Streams custom events you emit from your nodes.
   Example: In node: await writer.write({"my_custom_data": 123})
            Output: {"my_custom_data": 123}
   Use when you need to stream application-specific data.

9. "messages-tuple" - Messages with Metadata
   Like "messages" but includes additional metadata as tuples.
   Example: (message_chunk, {"langgraph_step": 1, "langgraph_node": "agent"})
   Use when you need message content + execution context together.

Usage:
    stream_mode="values"           # Full state snapshots
    stream_mode="messages"         # Token-by-token streaming
    stream_mode="updates"          # Delta changes only
    stream_mode=["values", "messages"]  # Multiple modes combined

Multiple Modes Example:
    You can combine multiple modes by passing them as a list:

    stream_mode=["messages", "custom"]

    Each chunk will have an `event` field indicating which mode it came from:
    - chunk.event == "messages" for LLM token chunks
    - chunk.event == "custom" for your custom events

    Example handling:

    async for chunk in client.runs.stream(
        thread_id,
        assistant_id,
        input={"messages": [HumanMessage(content=prompt)]},
        stream_mode=["messages", "custom"],
    ):
        if chunk.event == "messages":
            # Handle LLM token streaming
            print(chunk.data)
        elif chunk.event == "custom":
            # Handle your custom events
            print(chunk.data)
"""

import logging
from collections.abc import AsyncGenerator
from enum import Enum
from pprint import pformat
from typing import Any, cast

import httpx
from fastapi import HTTPException, status
from langchain_core.messages import HumanMessage
from langgraph_sdk import get_client
from langgraph_sdk.client import LangGraphClient
from langgraph_sdk.schema import Command, Config, StreamPart, Thread, ThreadState

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__, logging.INFO)


class AssistantID(str, Enum):
    """Assistant ID"""

    TASK_ASSISTANT = "task_assistant"
    TASK_TRANSLATION = "task_translation"


class LangGraphClientSDK:
    """
    Client for interacting with the LangGraph AI Agent service
    """

    __class_name__ = "LangGraphClientSDK"

    def __init__(self, base_url: str | None = None):
        """
        Initialize LangGraph client

        Args:
            base_url: Base URL for LangGraph API (defaults to settings)
        """
        self.base_url = base_url or settings.LANGGRAPH_API_URL
        self.timeout = 30.0

    def debug_chunk(self, user_id: str, task_id: str, thread_id: str, chunk: StreamPart, verbose: bool = False) -> None:
        """
        Debug a chunk of data

        Args:
            user_id: User ID
            task_id: Task ID
            thread_id: Thread ID
            chunk: Chunk of data
            verbose: Verbose output
        """

        if verbose:
            logger.debug(f"User: {user_id}, Task: {task_id}, Thread: {thread_id}, Chunk: {chunk}")
        else:
            if chunk.event == "values":
                data = cast(dict[str, Any], chunk.data)
                messages = data.get("messages", [])
                if messages:
                    logger.debug(
                        f"User: {user_id}, Task: {task_id}, Thread: {thread_id}, Last message: {pformat(messages[-1])}"
                    )
            logger.debug("----------------------------------------")

    async def get_client(self, caller: str | None = None) -> LangGraphClient:
        """
        Get a client for interacting with the LangGraph API server

        Returns:
            LangGraph client
        """
        __caller__ = "" if caller is None else f"- [caller: {caller}]"

        logger.info(f"{__caller__} Connecting to LangGraph service at {self.base_url}")

        try:
            client: LangGraphClient = get_client(url=self.base_url)
            return client
        except httpx.ConnectError:
            logger.error(f"{__caller__} Cannot connect to LangGraph service")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Cannot connect to LangGraph service"
            )
        except httpx.TimeoutException:
            logger.error(f"{__caller__} LangGraph service timeout")
            raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="LangGraph service timeout")
        except httpx.HTTPStatusError as e:
            logger.error(f"{__caller__} LangGraph error: {e.response.text}")
            raise HTTPException(status_code=e.response.status_code, detail=f"LangGraph error: {e.response.text}")
        except Exception as e:
            logger.error(f"{__caller__} Unexpected internal server error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Unexpected internal server error: {str(e)}"
            )

    async def create_thread(self) -> str:
        """
        Create a new thread using LangGraph thread service

        Returns:
            Thread creation result
        """
        __caller__ = "create_thread"

        client: LangGraphClient = await self.get_client(caller=__caller__)
        thread: Thread = await client.threads.create()
        return thread.get("thread_id", "(thread_id not found)")

    async def run_new_task(
        self,
        user_id: str,
        task_id: str,
        thread_id: str,
        assistant_id: AssistantID,
        prompt: str,
    ) -> AsyncGenerator[StreamPart]:
        """
        Ask a new task to the LangGraph assistant

        Args:
            user_id: User ID
            task_id: Task ID
            thread_id: Thread ID
            assistant_id: Assistant ID
            prompt: Prompt to ask the assistant

        Returns:
            Task result as a stream of chunks
        """
        __caller__ = "run_new_task"

        # Connect to the LangGraph API server
        client: LangGraphClient = await self.get_client(caller=__caller__)

        # Configure the task
        config: Config = {"configurable": {"user_id": user_id}}

        # Run the new task
        async for chunk in client.runs.stream(
            thread_id,
            assistant_id,
            input={"messages": [HumanMessage(content=prompt)]},
            config=config,
            stream_mode=["messages", "custom"],
        ):
            self.debug_chunk(user_id, task_id, thread_id, chunk, True)
            yield chunk

    # HITL: Human-in-the-loop
    async def run_hitl_task(
        self,
        user_id: str,
        task_id: str,
        thread_id: str,
        assistant_id: AssistantID,
        resume_msg: str,
    ) -> AsyncGenerator[StreamPart]:
        """
        Send a human message to the LangGraph thread

        Args:
            user_id: User ID
            task_id: Task ID
            thread_id: Thread ID
            assistant_id: Assistant ID
            resume_msg: Resume message to send to the assistant

        Returns:
            Human message sent result as a stream of chunks
        """
        __caller__ = "run_hitl_task"

        # Connect to the LangGraph API server
        client: LangGraphClient = await self.get_client(caller=__caller__)

        # Configure the task
        config: Config = {"configurable": {"user_id": user_id}}

        # Send the human message to the LangGraph thread
        async for chunk in client.runs.stream(
            thread_id,
            assistant_id,
            input=None,
            command=Command(resume=resume_msg),
            config=config,
            stream_mode="values",
        ):
            self.debug_chunk(user_id, task_id, thread_id, chunk, True)
            yield chunk

    async def parse_state(self, user_id: str, task_id: str, thread_id: str, assistant_id: AssistantID) -> None:
        """
        Parse and log the current state of a task

        Args:
            user_id: User ID
            task_id: Task ID
            thread_id: Thread ID
            assistant_id: Assistant ID
        """
        __caller__ = "parse_state"

        # Connect to the LangGraph API server
        client: LangGraphClient = await self.get_client(caller=__caller__)

        # Get and parse the current state
        current_state: ThreadState = await client.threads.get_state(thread_id)

        if assistant_id == AssistantID.TASK_TRANSLATION:
            await self.parse_translation_task_state(user_id, task_id, thread_id, current_state)
        else:
            logger.error(f"{__caller__} Unsupported assistant ID(or task name): {assistant_id}")
            raise ValueError(f"Unsupported assistant ID(or task name): {assistant_id})")

    async def parse_translation_task_state(
        self, user_id: str, task_id: str, thread_id: str, current_state: ThreadState
    ) -> None:
        """
        Parse and log the current state of a translation task

        Args:
            user_id: User ID
            task_id: Task ID
            thread_id: Thread ID
            current_state: Current state from client.threads.get_state()
        """

        # Print the full state structure
        logger.debug(
            f"User: {user_id}, Task: {task_id}, Thread: {thread_id}, Full State Structure: {pformat(current_state)}"
        )

        # Access specific components
        raw_values = current_state["values"]  # type: ignore[misc]
        values = cast(dict[str, Any] | None, raw_values) if isinstance(raw_values, dict) else None
        if values:
            # Get messages
            messages: list[Any] = values.get("messages", [])
            logger.debug(f"User: {user_id}, Task: {task_id}, Thread: {thread_id}, Number of messages: {len(messages)}")

            # Get analysis
            analysis: dict[str, Any] | None = values.get("analysis")
            if analysis:
                logger.debug(
                    f"User: {user_id}, Task: {task_id}, Thread: {thread_id}, Analysis available: {pformat(analysis)}"
                )
                logger.debug(
                    f"User: {user_id}, Task: {task_id}, Thread: {thread_id}, Summary: {analysis.get('summary')}"
                )
                logger.debug(
                    f"User: {user_id}, Task: {task_id}, Thread: {thread_id}, Target Language: {analysis.get('target_language')}"
                )
                logger.debug(
                    f"User: {user_id}, Task: {task_id}, Thread: {thread_id}, Source Language: {analysis.get('source_language')}"
                )
                logger.debug(
                    f"User: {user_id}, Task: {task_id}, Thread: {thread_id}, Category: {analysis.get('category')}"
                )
                logger.debug(
                    f"User: {user_id}, Task: {task_id}, Thread: {thread_id}, Number of words: {analysis.get('number_of_words')}"
                )
            else:
                logger.debug(f"User: {user_id}, Task: {task_id}, Thread: {thread_id}, No analysis available yet")
        else:
            logger.debug(f"User: {user_id}, Task: {task_id}, Thread: {thread_id}, No state values available")


# Singleton instance
langgraph_client: LangGraphClientSDK = LangGraphClientSDK()


"""
async for event in client.runs.stream(
    thread["thread_id"],
    assistant_id="agent",
    input={"messages": [input_message]},
    stream_mode="messages",):

    # Handle metadata events
    if event.event == "metadata":
        print(f"Metadata: Run ID - {event.data['run_id']}")
        print("-" * 50)

    # Handle partial message events
    elif event.event == "messages/partial":
        for data_item in event.data:
            # Process user messages
            if "role" in data_item and data_item["role"] == "user":
                print(f"Human: {data_item['content']}")
            else:
                # Extract relevant data from the event
                tool_calls = data_item.get("tool_calls", [])
                invalid_tool_calls = data_item.get("invalid_tool_calls", [])
                content = data_item.get("content", "")
                response_metadata = data_item.get("response_metadata", {})

                if content:
                    print(f"AI: {content}")

                if tool_calls:
                    print("Tool Calls:")
                    print(format_tool_calls(tool_calls))

                if invalid_tool_calls:
                    print("Invalid Tool Calls:")
                    print(format_tool_calls(invalid_tool_calls))

                if response_metadata:
                    finish_reason = response_metadata.get("finish_reason", "N/A")
                    print(f"Response Metadata: Finish Reason - {finish_reason}")

        print("-" * 50)
"""
