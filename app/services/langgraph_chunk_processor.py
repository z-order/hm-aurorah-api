"""
LangGraph Chunk Processor

This module provides classes and functions for processing streaming chunks
from LangGraph AI Agent responses.

Class Hierarchy:
----------------
LangGraphChunkCollector (base)
├── TranslationChunkCollector (shared translation logic)
│   ├── TaskTranslationA1_ChunkCollector
│   └── TaskTranslationA2_ChunkCollector
├── SummarizationChunkCollector (future)
├── ChatbotChunkCollector (future)
└── GlossaryChunkCollector (future)

Functions:
    process_langgraph_chunk: Process a single chunk and broadcast to message queue
"""

import json
import logging
import re
from typing import Any, cast

from app.core.logger import get_logger
from app.core.rsmqueue import RedisStreamMessageQueue
from app.services.langgraph_client import ParsedChunk
from app.utils.utils_text import analyze_raw_text_to_json

logger = get_logger(__name__, logging.DEBUG)


# =============================================================================
# BASE CLASS: LangGraphChunkCollector
# =============================================================================


class LangGraphChunkCollector:
    """
    Base collector class for accumulating and processing chunks from LangGraph.

    This class collects streaming chunks from the AI agent and provides
    general-purpose methods for chunk collection.

    Attributes:
        raw_chunks: List of raw chunk data received from the stream
        ai_message_content: Accumulated AI message content
        metadata: Metadata from the stream (run_id, etc.)
    """

    def __init__(self) -> None:
        """Initialize the chunk collector."""
        self.raw_chunks: list[ParsedChunk] = []
        self.ai_message_content: str = ""
        self.metadata: dict[str, Any] = {}

    def add_chunk(self, chunk_data: ParsedChunk) -> None:
        """
        Add a parsed chunk to the collector.

        Args:
            chunk_data: Parsed chunk data from langgraph_client.parse_chunk()
        """
        self.raw_chunks.append(chunk_data)

    def append_ai_content(self, content: str) -> None:
        """
        Append content to the accumulated AI message.

        Args:
            content: Text content to append
        """
        self.ai_message_content += content

    def set_metadata(self, key: str, value: Any) -> None:
        """
        Set metadata value.

        Args:
            key: Metadata key
            value: Metadata value
        """
        self.metadata[key] = value

    def get_ai_content(self) -> str:
        """
        Get the accumulated AI message content.

        Returns:
            The accumulated AI message content string
        """
        return self.ai_message_content

    def get_metadata(self, key: str) -> Any:
        """
        Get metadata value by key.

        Args:
            key: Metadata key

        Returns:
            Metadata value or None if not found
        """
        return self.metadata.get(key)

    def format_result(self) -> dict[str, Any]:
        """
        Format the collected chunks into the final result structure.

        Override this method in subclasses to provide agent-specific formatting.

        Returns:
            Formatted result as dictionary
        """
        return {"content": self.ai_message_content}


# =============================================================================
# TRANSLATION COLLECTORS
# =============================================================================


class TranslationChunkCollector(LangGraphChunkCollector):
    """
    Shared collector class for translation agents.

    Extends LangGraphChunkCollector with common methods for formatting
    translation results from AI agent responses.

    AI Agent Output Format:
    -----------------------
    The AI agent returns:
    1. JSON metadata (summary, plot, category, source_language, target_language, etc.)
    2. <translated_text>...</translated_text> section with ┼N┼ markers

    Example AI output:
    {"summary": "...", "plot": "...", "category": "...", ...}
    <translated_text> ┼1┼First translated sentence.┼2┼Second sentence... </translated_text>
    """

    def format_result(self) -> dict[str, Any]:
        """
        Format the collected chunks into the final translated_text structure.

        This method extracts both:
        - JSON metadata properties (stored under "metadata" key)
        - <translated_text> section parsed into segments

        Final output format:
        {
            "segments": [
                {"sid": 1, "text": "First translated sentence."},
                {"sid": 2, "text": "Second sentence..."},
                ...
            ],
            "metadata": {
                "summary": "...",
                "source_language": "English",
                "target_language": "Korean",
                ...
            }
        }

        Returns:
            Formatted translated_text as dictionary with segments and metadata
        """
        if not self.ai_message_content:
            return {"segments": []}

        translated_text: dict[str, Any] = {"segments": []}

        # ---------------------------------------------------------------------
        # STEP 1: Extract JSON metadata from AI response
        # The JSON object appears before <translated_text> tag
        # Store all metadata under "metadata" key
        # ---------------------------------------------------------------------
        metadata = self._extract_metadata_json()
        if metadata:
            translated_text["metadata"] = metadata

        # ---------------------------------------------------------------------
        # STEP 2: Extract <translated_text>...</translated_text> section
        # ---------------------------------------------------------------------
        content_to_parse = self._extract_translated_text_content()

        # ---------------------------------------------------------------------
        # STEP 3: Try JSON parse first (AI may return JSON with segments),
        #         then fall back to ┼N┼ marker parsing
        # ---------------------------------------------------------------------
        json_segments = self._try_parse_json_segments(content_to_parse)
        if json_segments is not None:
            translated_text["segments"] = json_segments
        else:
            segments_data = analyze_raw_text_to_json(content_to_parse)
            translated_text["segments"] = segments_data.get("segments", [])

        # Log success
        segments_count = len(translated_text.get("segments", []))
        if segments_count > 0:
            logger.info(f"Parsed {segments_count} segments from AI response")
        else:
            logger.warning("No segments parsed from AI response")
            translated_text["_raw"] = self.ai_message_content

        return translated_text

    def _extract_translated_text_content(self) -> str:
        """
        Extract content from <translated_text>...</translated_text> section.

        Returns:
            Extracted content or full ai_message_content if no tags found
        """
        content_to_parse = self.ai_message_content

        # Try to extract content between <translated_text> tags
        translated_text_match = re.search(
            # () : capture group
            # .* : matches any character (.) zero or more times (*)
            # ?  : non-greedy; stops at first closing tag
            r"<translated_text>(.*?)</translated_text>",
            self.ai_message_content,
            # makes . match newlines too, so it works across multiple lines
            re.DOTALL,
        )

        if translated_text_match:
            # .group(0) : returns the entire match, .group(1) : returns only what's inside the parentheses.
            content_to_parse = translated_text_match.group(1).strip()
        else:
            # If no tags found, try to use the entire content
            # (AI might return just the marked text without tags)
            logger.debug("No <translated_text> tags found, parsing entire content")

        return content_to_parse

    def _extract_metadata_json(self) -> dict[str, Any] | None:
        """
        Extract JSON metadata from AI response.

        The AI agent returns JSON metadata before <translated_text> tag:
        {"summary": "...", "plot": "...", ...}
        <translated_text>...</translated_text>

        Returns:
            Extracted metadata dictionary or None if not found
        """
        if not self.ai_message_content:
            return None

        # Try to find JSON object at the beginning or before <translated_text>
        # Pattern: {...} that appears before <translated_text> or at start
        json_match = re.search(
            r"(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})\s*(?:<translated_text>|$)",
            self.ai_message_content,
            re.DOTALL,
        )

        if not json_match:
            # Try simpler pattern - just find first JSON object
            json_match = re.search(r"(\{.*?\})\s*<translated_text>", self.ai_message_content, re.DOTALL)

        if json_match:
            try:
                parsed = json.loads(json_match.group(1))
                if isinstance(parsed, dict):
                    metadata: dict[str, Any] = cast(dict[str, Any], parsed)
                    logger.info(f"Extracted {len(metadata)} metadata fields from AI response")
                    return metadata
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse metadata JSON: {e}")

        return None

    def _try_parse_json_segments(self, content: str) -> list[dict[str, Any]] | None:
        """
        Try to parse content as JSON with a segments array.

        The AI agent may return translation as a JSON object:
        {"segments": [{"sid": 1, "text": "..."}, ...]}

        or

        <translated_text> ┼1┼First translated sentence.┼2┼Second sentence... </translated_text>

        If content is valid JSON with segments, return the segment list directly.
        Otherwise return None so the caller falls back to ┼N┼ marker parsing.

        Returns:
            List of segment dicts if valid JSON with segments, else None
        """
        stripped = content.strip()
        if not stripped.startswith("{"):
            # return None so the caller falls back to ┼N┼ marker parsing
            return None

        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            return None

        if not isinstance(parsed, dict):
            return None

        segments = parsed.get("segments")  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
        if not isinstance(segments, list) or len(segments) == 0:  # pyright: ignore[reportUnknownArgumentType]
            return None

        # Validate segment structure
        valid: list[dict[str, Any]] = []
        for seg in segments:  # pyright: ignore[reportUnknownVariableType]
            if isinstance(seg, dict) and "sid" in seg and "text" in seg:
                valid.append({"sid": seg["sid"], "text": str(seg["text"])})  # pyright: ignore[reportUnknownArgumentType]

        if valid:
            logger.info(f"Parsed {len(valid)} segments from JSON response (direct)")
            return valid

        return None


class TaskTranslationA1_ChunkCollector(TranslationChunkCollector):
    """
    Chunk collector for task_translation_a1 agent.

    Currently uses the same format as TranslationChunkCollector.
    Override format_result() if a1-specific formatting is needed.
    """

    pass


class TaskTranslationA2_ChunkCollector(TranslationChunkCollector):
    """
    Chunk collector for task_translation_a2 agent.

    Override format_result() if a2-specific formatting is needed.
    """

    pass


# =============================================================================
# SUMMARIZATION COLLECTORS (Future)
# =============================================================================


class SummarizationChunkCollector(LangGraphChunkCollector):
    """
    Shared collector class for summarization agents.

    Override format_result() to implement summarization-specific formatting.
    """

    def format_result(self) -> dict[str, Any]:
        """
        Format the collected chunks into the final summary structure.

        Returns:
            Formatted summary as dictionary
        """
        # TODO: Implement summarization-specific formatting
        return {"summary": self.ai_message_content}


# =============================================================================
# CHATBOT COLLECTORS (Future)
# =============================================================================


class ChatbotChunkCollector(LangGraphChunkCollector):
    """
    Shared collector class for chatbot agents.

    Override format_result() to implement chatbot-specific formatting.
    """

    def format_result(self) -> dict[str, Any]:
        """
        Format the collected chunks into the final chatbot response structure.

        Returns:
            Formatted chatbot response as dictionary
        """
        # TODO: Implement chatbot-specific formatting
        return {"message": self.ai_message_content}


# =============================================================================
# GLOSSARY COLLECTORS (Future)
# =============================================================================


class GlossaryChunkCollector(LangGraphChunkCollector):
    """
    Shared collector class for glossary agents.

    Override format_result() to implement glossary-specific formatting.
    """

    def format_result(self) -> dict[str, Any]:
        """
        Format the collected chunks into the final glossary structure.

        Returns:
            Formatted glossary as dictionary
        """
        # TODO: Implement glossary-specific formatting
        return {"glossary": self.ai_message_content}


# =============================================================================
# CHUNK COLLECTOR FACTORY
# =============================================================================

# Mapping of ai_agent_id to chunk collector class
CHUNK_COLLECTOR_MAP: dict[str, type[LangGraphChunkCollector]] = {
    # Translation agents
    "task_translation_a1": TaskTranslationA1_ChunkCollector,
    "task_translation_a2": TaskTranslationA2_ChunkCollector,
    # Summarization agents (future)
    # "task_summarization_a1": SummarizationChunkCollector,
    # Chatbot agents (future)
    # "task_chatbot_a1": ChatbotChunkCollector,
    # Glossary agents (future)
    # "task_glossary_a1": GlossaryChunkCollector,
}


def get_langgraph_chunk_collector(ai_agent_id: str) -> LangGraphChunkCollector:
    """
    Get the appropriate chunk collector instance for the given AI agent.

    Args:
        ai_agent_id: The AI agent ID (e.g., "task_translation_a1", "task_translation_a2")

    Returns:
        Chunk collector instance for the specified agent

    Raises:
        ValueError: If the ai_agent_id is not supported
    """
    collector_class = CHUNK_COLLECTOR_MAP.get(ai_agent_id)

    if collector_class is None:
        raise ValueError(f"Unsupported ai_agent_id: {ai_agent_id}")

    return collector_class()


# =============================================================================
# CHUNK PROCESSING FUNCTION
# =============================================================================


async def process_langgraph_chunk(
    mq: RedisStreamMessageQueue,
    channel_id: str,
    parsed_chunk: ParsedChunk | None,
    chunk_collector: LangGraphChunkCollector,
) -> None:
    """
    Process a single chunk from the LangGraph stream.

    This function:
    1. Collects chunk data for final formatting
    2. Broadcasts progress to client via message queue
    3. Extracts AI message content for result

    Args:
        mq: Redis Stream Message Queue instance
        channel_id: Channel ID for broadcasting to client
        parsed_chunk: Parsed chunk from langgraph_client.parse_chunk()
        chunk_collector: Collector instance to accumulate chunks
    """
    if not parsed_chunk:
        return

    # Store raw chunk for analysis
    chunk_collector.add_chunk(parsed_chunk)

    # Track last message type for consistent message structure
    last_message_type: str = "ai"

    # -------------------------------------------------------------------------
    # Handle metadata, tasks, or updates event
    # -------------------------------------------------------------------------
    if parsed_chunk and parsed_chunk["event"] in ["metadata", "tasks", "updates"]:
        # Store run_id from metadata for later use
        if parsed_chunk["event"] == "metadata":
            if parsed_chunk.get("run_id"):
                chunk_collector.set_metadata("run_id", parsed_chunk["run_id"])

        # Prepare the payload for the langgraph stream chunk
        payload = {
            "type": parsed_chunk["event"],
            "data": parsed_chunk,
        }

        # Send the langgraph stream chunk to the client
        await mq.broadcast(channel_id, "langgraph_stream_chunk", payload)
        logger.debug(f"LangGraph stream chunk broadcasted to channel: {channel_id}")

    # -------------------------------------------------------------------------
    # Process the events chunk
    # -------------------------------------------------------------------------
    elif parsed_chunk and parsed_chunk["event"] == "events":
        # Start of the stream message
        if parsed_chunk["event_name"] == "on_chat_model_start":
            pass

        elif parsed_chunk["event_name"] == "on_chat_model_stream":
            last_message_type = (
                "ai" if parsed_chunk["is_ai_message"] else "tool" if parsed_chunk["is_tool_call"] else "unknown"
            )

            # Collect AI message content for final result
            chunk_data = parsed_chunk.get("chunk_data")
            if parsed_chunk.get("is_ai_message") and chunk_data and isinstance(chunk_data, str):
                chunk_collector.append_ai_content(chunk_data)

            # Send the stream message chunk to the client
            await mq.broadcast(
                channel_id,
                "model_stream_chunk",
                {
                    "type": last_message_type,
                    "message": parsed_chunk["chunk_data"],
                    "status": "processing",
                },
            )

        # End of the stream message
        elif parsed_chunk["event_name"] == "on_chat_model_end":
            # Send the final stream message chunk to the client
            await mq.broadcast(
                channel_id,
                "model_stream_chunk",
                {
                    "type": last_message_type,
                    "message": "",
                    "status": "completed",
                },
            )
