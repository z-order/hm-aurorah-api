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

Event Hierarchy in stream_mode=["updates", "tasks", "events"]:

    metadata (run start)
    ├── tasks (node triggered)
    ├── events (detailed execution)
    │   ├── on_chain_start
    │   ├── on_chat_model_start
    │   ├── on_chat_model_stream (multiple)
    │   ├── on_chat_model_end
    │   └── on_chain_end
    ├── updates (node result)
    └── tasks (node completed)
"""

import logging
from collections.abc import AsyncGenerator
from enum import Enum
from pprint import pformat
from typing import Any, Literal, TypedDict, cast

import httpx
from fastapi import HTTPException, status
from langchain_core.messages import HumanMessage
from langgraph_sdk import get_client
from langgraph_sdk.client import LangGraphClient
from langgraph_sdk.schema import Command, Config, StreamPart, Thread, ThreadState

from app.core.config import settings
from app.core.logger import get_logger

# Enable/disable debug logging in debug_chunk()
LOG_DEBUG_CHUNK = False

logger = get_logger(__name__, logging.DEBUG)


class AssistantID(str, Enum):
    """Assistant ID"""

    TASK_ASSISTANT = "task_assistant"
    TASK_TRANSLATION = "task_translation"


class ParsedChunk_Metadata(TypedDict):
    """Parsed chunk metadata"""

    event: Literal["metadata"]
    run_id: str


class ParsedChunk_Values(TypedDict):
    """Parsed chunk values"""

    event: Literal["values"]
    messages: list[dict[str, Any]]
    is_interrupted: bool
    interrupt_msg: str | None


class ParsedChunk_Tasks(TypedDict):
    """Parsed chunk tasks"""

    event: Literal["tasks"]
    task_id: str
    task_name: str
    task_error: str | None
    task_triggers: str | None
    is_node_started: bool
    is_node_completed: bool
    is_interrupted: bool
    interrupt_msg: str | None


class ParsedChunk_Updates(TypedDict):
    """Parsed chunk updates"""

    event: Literal["updates"]
    node_name: str
    node_output: dict[str, Any]
    is_interrupted: bool
    interrupt_msg: str | None


class ParsedChunk_Events(TypedDict):
    """Parsed chunk events"""

    event: Literal["events"]
    event_name: str
    is_ai_message: bool
    is_tool_call: bool
    event_data: dict[str, Any]
    chunk_data: str | dict[str, Any] | None


ParsedChunk = ParsedChunk_Metadata | ParsedChunk_Values | ParsedChunk_Tasks | ParsedChunk_Updates | ParsedChunk_Events


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
        if not LOG_DEBUG_CHUNK:
            return

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
        translation_role: str = """"You are a professional translation/localization expert.\
            If the source language is Korean then,
            Target language: English.\
            Target country: United States.\
            Target city: New York.\
            If the source language is English then,
            Target language: Korean.\
            Target country: South Korea.\
            Target city: Seoul.\
            Target audience: General public.\
            Target purpose: Web novel translation. \
            """.strip()
        config: Config = {"configurable": {"user_id": user_id, "translation_role": translation_role}}

        # Run the new task
        async for chunk in client.runs.stream(  # type: ignore[misc]
            thread_id,
            assistant_id,
            input={"messages": [HumanMessage(content=prompt)]},  # type: ignore[arg-type]
            config=config,
            stream_mode=["updates", "tasks", "events"],
        ):
            self.debug_chunk(user_id, task_id, thread_id, cast(StreamPart, chunk), True)
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
            stream_mode=["updates", "tasks", "events"],
        ):
            self.debug_chunk(user_id, task_id, thread_id, chunk, True)
            yield chunk

    async def parse_chunk(self, user_id: str, task_id: str, thread_id: str, chunk: StreamPart) -> ParsedChunk | None:
        """
        Parse and log a chunk of data

        Args:
            user_id: User ID
            task_id: Task ID
            thread_id: Thread ID
            chunk: Chunk of data

        Returns:
            Parsed chunk or None if the chunk is not a valid chunk
        """

        # If chunk includes StreamPart(event='metadata', data={'run_id': '...'}), update last_run_id into task.
        if chunk.event == "metadata" and isinstance(chunk.data, dict) and "run_id" in chunk.data:  # type: ignore[arg-type]
            parsed_metadata: ParsedChunk_Metadata = {
                "event": "metadata",
                "run_id": cast(str, chunk.data["run_id"]),
            }
            return parsed_metadata

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
                interrupt_msg: str = interrupt_data[0]["value"]["msg"]  # pyright: ignore[reportRedeclaration]
                interrupted_values: ParsedChunk_Values = {
                    "event": "values",
                    "messages": [],
                    "is_interrupted": True,
                    "interrupt_msg": interrupt_msg,
                }
                return interrupted_values
            else:
                logger.error(
                    f"User: {user_id}, Task: {task_id}, Thread: {thread_id}, Invalid interrupt data: {interrupt_data}"
                )
                return None

        if chunk.event == "values":
            data = cast(dict[str, Any], chunk.data)
            messages = data.get("messages", [])
            if messages:
                logger.debug(
                    f"User: {user_id}, Task: {task_id}, Thread: {thread_id}, Last message: {pformat(messages[-1])}"
                )
                parsed_values: ParsedChunk_Values = {
                    "event": "values",
                    "messages": messages,
                    "is_interrupted": False,
                    "interrupt_msg": None,
                }
                return parsed_values

        if chunk.event == "tasks":
            task_data = cast(dict[str, Any], chunk.data)

            # Node TRIGGERED (starting)
            if "input" in task_data and "result" not in task_data:
                logger.info(
                    f"User: {user_id}, Task: {task_id}, Thread: {thread_id}, 🟢 Node STARTED: {task_data['name']}"
                )
                logger.info(f"User: {user_id}, Task: {task_id}, Thread: {thread_id},   Task ID: {task_data['id']}")
                logger.info(
                    f"User: {user_id}, Task: {task_id}, Thread: {thread_id},   Triggers: {task_data['triggers']}"
                )

                started_tasks: ParsedChunk_Tasks = {
                    "event": "tasks",
                    "task_id": task_data["id"],
                    "task_name": task_data["name"],
                    "task_triggers": task_data["triggers"],
                    "task_error": None,
                    "is_node_started": True,
                    "is_node_completed": False,
                    "is_interrupted": False,
                    "interrupt_msg": None,
                }
                return started_tasks

            # Node COMPLETED
            elif "result" in task_data:
                logger.info(
                    f"User: {user_id}, Task: {task_id}, Thread: {thread_id}, 🔵 Node COMPLETED: {task_data['name']}"
                )
                logger.info(f"User: {user_id}, Task: {task_id}, Thread: {thread_id},   Task ID: {task_data['id']}")
                logger.info(f"User: {user_id}, Task: {task_id}, Thread: {thread_id},   Error: {task_data['error']}")
                logger.info(
                    f"User: {user_id}, Task: {task_id}, Thread: {thread_id},   Interrupts: {task_data['interrupts']}"
                )

                # StreamPart(
                #     event='tasks',
                #     data={
                #         'id': 'd814f74f-17fb-2d32-ac87-22361d71dc72',
                #         'name': 'analyze_original_text',
                #         'error': None,
                #         'result': {},
                #         'interrupts': [
                #             {
                #                 'value': {
                #                     'call_chain': [
                #                         'ask_user_for_clarifying_task',
                #                         '__human_in_the_loop',
                #                         'interrupt',
                #                     ],
                #                     'next_node': 'check_analyzed_result_by_llm',
                #                     'cause': 'ASKU found',
                #                     'msg': (
                #                         '번역/현지화 작업을 진행하기 위해 몇 가지 정보가 필요합니다. 다음 사항들을 알려주시겠습니까?\n'
                #                         '\n'
                #                         '1. 목표 언어: 어떤 언어로 번역하시겠습니까?\n'
                #                         '2. 목표 국가: 어느 국가를 대상으로 하시겠습니까?\n'
                #                         '3. 대상 독자: 누구를 위한 번역인가요? (어린이, 청소년, 성인, 노인, 일반 대중 등)\n'
                #                         '4. 번역 목적: 이 번역의 목적이나 용도는 무엇인가요?\n'
                #                         '\n'
                #                         '이 정보들을 제공해 주시면 더 정확하고 적절한 번역을 제공할 수 있습니다.'
                #                     ),
                #                 },
                #                 'id': 'f9dff66cdb4d0284925e6df7eddef25c',
                #             }
                #         ],
                #     },
                # )
                is_interrupted: bool = len(task_data.get("interrupts", [])) > 0  # pyright: ignore[reportRedeclaration]
                interrupt_msg: str | None = (  # pyright: ignore[reportRedeclaration]
                    task_data.get("interrupts", [])[0].get("value", {}).get("msg", None) if is_interrupted else None
                )

                completed_tasks: ParsedChunk_Tasks = {
                    "event": "tasks",
                    "task_id": task_data["id"],
                    "task_name": task_data["name"],
                    "task_error": task_data.get("error", None),
                    "task_triggers": None,
                    "is_node_started": False,
                    "is_node_completed": True,
                    "is_interrupted": is_interrupted,
                    "interrupt_msg": interrupt_msg,
                }
                return completed_tasks

        if chunk.event == "updates":
            update_data = cast(dict[str, Any], chunk.data)
            # The key is the node name that just completed
            for node_name, node_output in update_data.items():
                # Logs all items to the console
                #  - It might be a single item (a single node).
                #  - If there are multiple nodes, you will see them here, check the exceptions for multiple nodes later.
                logger.info(
                    f"User: {user_id}, Task: {task_id}, Thread: {thread_id}, ✅ Node COMPLETED (OUTPUT): {node_name}"
                )
                logger.info(f"User: {user_id}, Task: {task_id}, Thread: {thread_id},   Output: {node_output}")

            # Return the first item's update data
            for node_name, node_outputs in update_data.items():
                # Node OUTPUT (result)
                # --------------------------------------------------------------------------------------
                #
                # StreamPart(
                #     event="updates",
                #     data={
                #         "upload_original_text": {
                #             "options": {
                #                 "llm_model": "claude-sonnet-4-20250514",
                #                 "temperature": 0.0
                #             },
                #             "keys": {
                #                 "original_text": "19125091-685e-4626-ae49-fe031270125f",
                #                 "translation_rules": "5fcfd2f1-b192-4a5e-8986-47a5380774f6"
                #             },
                #             "messages": []
                #         }
                #     }
                # )
                #
                # StreamPart(
                #     event="updates",
                #     data={
                #         "__interrupt__": [
                #             {
                #                 "value": {
                #                     "call_chain": [
                #                         "ask_user_for_clarifying_task",
                #                         "__human_in_the_loop",
                #                         "interrupt",
                #                     ],
                #                     "next_node": "check_analyzed_result_by_llm",
                #                     "cause": "ASKU found",
                #                     "msg": (
                #                         "번역/현지화 작업을 진행하기 위해 몇 가지 정보가 필요합니다. 다음 사항들을 알려주시겠습니까?\n"
                #                         "\n"
                #                         "1. 목표 언어: 어떤 언어로 번역하시겠습니까?\n"
                #                         "2. 목표 국가: 어느 국가를 대상으로 하시겠습니까?\n"
                #                         "3. 대상 독자: 누구를 위한 번역인가요? (어린이, 청소년, 성인, 노인, 일반 대중 등)\n"
                #                         "4. 번역 목적: 이 번역의 목적이나 용도는 무엇인가요?\n"
                #                         "\n"
                #                         "이 정보들을 제공해 주시면 더 정확하고 적절한 번역을 제공할 수 있습니다."
                #                     ),
                #                 },
                #                 "id": "f9dff66cdb4d0284925e6df7eddef25c",
                #             }
                #         ]
                #     },
                # )
                # Use the first item in "__interrupt__" list
                if isinstance(node_outputs, list) and isinstance(node_outputs[0], dict):
                    node_output = cast(dict[str, Any], node_outputs[0])
                    is_interrupted: bool = len(node_output.get("__interrupt__", [])) > 0
                    interrupt_msg: str | None = (
                        node_output.get("__interrupt__", [])[0].get("value", {}).get("msg", None)
                        if is_interrupted
                        else None
                    )
                    parsed_updates: ParsedChunk_Updates = {  # pyright: ignore[reportRedeclaration]
                        "event": "updates",
                        "node_name": node_name,
                        "node_output": node_output,
                        "is_interrupted": is_interrupted,
                        "interrupt_msg": interrupt_msg,
                    }
                    return parsed_updates
                elif isinstance(node_outputs, dict):
                    parsed_updates: ParsedChunk_Updates = {
                        "event": "updates",
                        "node_name": node_name,
                        "node_output": node_outputs,
                        "is_interrupted": False,
                        "interrupt_msg": None,
                    }
                    return parsed_updates
                else:
                    logger.error(
                        f"User: {user_id}, Task: {task_id}, Thread: {thread_id}, Invalid node output: {node_outputs}"
                    )
                    return None

        if chunk.event == "events":
            event_data = cast(dict[str, Any], chunk.data)

            if event_data.get("event") == "on_chat_model_start":
                logger.debug(f"User: {user_id}, Task: {task_id}, Thread: {thread_id}, ⏩ on_chat_model_start")

                parsed_events_start: ParsedChunk_Events = {
                    "event": "events",
                    "event_name": "on_chat_model_start",
                    "is_ai_message": False,
                    "is_tool_call": False,
                    "event_data": event_data,
                    "chunk_data": None,
                }
                return parsed_events_start

            if event_data.get("event") == "on_chat_model_end":
                # Print the end of the on_chat_model_stream event to the console
                print("  <<<<------------ END OF on_chat_model_stream EVENT")

                logger.debug(f"User: {user_id}, Task: {task_id}, Thread: {thread_id}, ⏪ on_chat_model_end")

                parsed_events_end: ParsedChunk_Events = {
                    "event": "events",
                    "event_name": "on_chat_model_end",
                    "is_ai_message": False,
                    "is_tool_call": False,
                    "event_data": event_data,
                    "chunk_data": None,
                }
                return parsed_events_end

            if event_data.get("event") == "on_chat_model_stream":
                event_data_in_data = cast(dict[str, Any], event_data.get("data"))
                chunk_data = event_data_in_data.get("chunk", {})

                # AI text message chunk (Heierachy: data -> data -> chunk -> content)
                if (
                    chunk_data.get("content")
                    and isinstance(chunk_data["content"], str)
                    and chunk_data.get("type") == "AIMessageChunk"
                ):
                    print(chunk_data["content"], end="", flush=True)

                    parsed_events_text: ParsedChunk_Events = {  # pyright: ignore[reportRedeclaration]
                        "event": "events",
                        "event_name": "on_chat_model_stream",
                        "is_ai_message": True,
                        "is_tool_call": False,
                        "event_data": event_data_in_data,
                        "chunk_data": chunk_data["content"],
                    }
                    return parsed_events_text

                #
                # AI tool call chunk (Heierachy: data -> data -> chunk -> tool_call_chunks[] -> args)
                #
                # Logs all items to the console
                #  - It might be a single item (a single node).
                #  - If there are multiple nodes, you will see them here, check the exceptions for multiple nodes later.
                for tool_call_chunk in chunk_data.get("tool_call_chunks", []):
                    # if tool_call_chunk.get('name'): print(f"[{tool_call_chunk['name']}]")
                    if tool_call_chunk.get("args"):
                        print(tool_call_chunk["args"], end="", flush=True)

                # Return the first item's tool call chunk
                for tool_call_chunk in chunk_data.get("tool_call_chunks", []):
                    if tool_call_chunk.get("args"):
                        parsed_events_tool_call: ParsedChunk_Events = {  # pyright: ignore[reportRedeclaration]
                            "event": "events",
                            "event_name": "on_chat_model_stream",
                            "is_ai_message": False,
                            "is_tool_call": True,
                            "event_data": event_data_in_data,
                            "chunk_data": tool_call_chunk["args"],
                        }
                        return parsed_events_tool_call

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
