"""
Redis Stream Message Queue (rsmqueue.py)
----------------------------------------
Reusable Redis Stream-based message queue for chat, notifications, and event streaming.

This module provides a consumer group-based message queue using Redis Streams (XADD, XREADGROUP, XACK).
It supports multiple consumers, at-least-once delivery semantics, and graceful handling of disconnections.

Key features:
- Consumer groups for distributed message processing
- Automatic stream and consumer group creation
- At-least-once delivery with XACK acknowledgments
- Consumer cleanup on disconnect
- SSE (Server-Sent Events) support for web clients
- Channel-based message routing

OPTIMIZATIONS APPLIED:
- JSON optimization: Compact JSON output with separators=(",", ":")
- Redis pipeline: Batched commands to reduce network round-trips
- Type hints: TYPE_CHECKING for better IDE support without runtime overhead
- Memory optimization: __slots__ to reduce memory footprint per instance
- Graceful error handling with contextlib.suppress
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncGenerator
from contextlib import suppress
from typing import TYPE_CHECKING, Any, Literal

from redis import asyncio as aioredis  # type: ignore[import-untyped]
from uuid_utils import uuid7

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__, logging.INFO)

# OPTIMIZATION: TYPE_CHECKING for better IDE support without runtime overhead
if TYPE_CHECKING:
    from redis.asyncio import Redis  # type: ignore[import-untyped]


class RedisStreamMessageQueue:
    """
    A reusable wrapper around Redis Streams with consumer groups for message queuing.

    Redis Keys:
        Each "channel" is a Redis Stream: <prefix><channel_id>

    Consumer Groups:
        Each stream has a consumer group for distributed processing.

        IMPORTANT - Broadcasting to Multiple Browsers:
        For the same Redis Stream (channel):
        - Different consumer groups = each group gets ALL messages (broadcast)
        - Same consumer group = messages are DISTRIBUTED (only one consumer gets each message)

        Example 1 - BROADCAST (each browser gets all messages):
            Stream: mq:channel:chat-123
            - Consumer Group A (browser 1): gets message 1, 2, 3
            - Consumer Group B (browser 2): gets message 1, 2, 3
            - Consumer Group C (browser 3): gets message 1, 2, 3

        Example 2 - DISTRIBUTED (messages split across browsers):
            Stream: mq:channel:chat-123
            - Consumer Group "mq-consumer-default":
                - Consumer 1 (browser 1): gets message 1, 3
                - Consumer 2 (browser 2): gets message 2
                - Consumer 3 (browser 3): (none yet)

        To broadcast to all browsers, each browser needs its own consumer group:
            RedisStreamMessageQueue(consumer_group=f"mq-consumer-{consumer_id}")

    Stored entry shape:
        { "data": "<json string>" }
        Example: { "data": '{"sender":"alice","text":"hello","type":"message"}' }

    Typical usage:

        # Producer
        mq = RedisStreamMessageQueue("redis://localhost")
        await mq.send("channel-1", {"sender": "alice", "text": "hello"})

        # Consumer
        async for msg_id, payload in mq.consume("channel-1", "consumer-1"):
            print(msg_id, payload)
            # Message is auto-acknowledged after yielding

    Notes on Stream IDs:
        - Stream IDs look like "1716400000000-0" (millisecond timestamp + sequence).
        - Use ">" in XREADGROUP to get only new undelivered messages.
        - Use "0" to get pending messages for this consumer.
    """

    # OPTIMIZATION: __slots__ to reduce memory footprint per instance
    __slots__ = ("r", "prefix", "group", "stream_id_type", "maxlen", "ttl", "block_ms", "read_count")

    def __init__(
        self,
        redis_url: str | None = None,
        *,
        stream_prefix: str = "mq:channel:",
        consumer_group: str = "mq-consumer-default",
        stream_id_type: Literal["stream_from_beginning", "stream_from_new_only"] = "stream_from_beginning",
        maxlen: int = 10000,  # 10,000 messages
        ttl_seconds: int = 3600,  # 1 hour
        block_ms: int = 15000,  # 15 seconds
        read_count: int = 10,  # 10 messages
        decode_responses: bool = True,
    ):
        """
        Args:
            redis_url: e.g. "redis://localhost:6379/0" (defaults to config.redis_url)
            stream_prefix: prefix for stream keys, e.g. "mq:channel:" -> "mq:channel:<channel_id>"
            consumer_group: name of the consumer group for distributed processing
            maxlen: number of entries kept per stream (XADD MAXLEN ~)
            ttl_seconds: expiration time (EXPIRE) for each stream (default 24h)
            block_ms: default blocking time for consume() calls (default 15s)
            read_count: number of messages to read per XREADGROUP call
            decode_responses: if True, decode bytes to strings
        """
        url = redis_url or settings.redis_url
        self.r: Redis = aioredis.from_url(url, decode_responses=decode_responses)  # type: ignore[no-untyped-call]
        self.prefix: str = stream_prefix
        self.group: str = consumer_group
        self.stream_id_type: Literal["stream_from_beginning", "stream_from_new_only"] = stream_id_type
        self.maxlen: int = maxlen
        self.ttl: int = ttl_seconds
        self.block_ms: int = block_ms
        self.read_count: int = read_count

    # -------------------- utilities --------------------
    def key(self, channel_id: str) -> str:
        """Generate Redis key for a channel ID."""
        return f"{self.prefix}{channel_id}"

    @staticmethod
    def _encode_payload(data: dict[str, Any]) -> dict[str, str]:
        """Encode payload data to Redis stream format."""
        # OPTIMIZATION: Compact JSON with separators=(",", ":") - no spaces after separators
        #  - default=str is to handle non-serializable objects like datetime.datetime, uuid.UUID, etc.
        return {"data": json.dumps(data, ensure_ascii=False, separators=(",", ":"), default=str)}

    @staticmethod
    def _decode_payload(fields: dict[str, str]) -> dict[str, Any]:
        """Decode Redis stream fields to payload data."""
        return json.loads(fields["data"])

    async def ensure_group(self, channel_id: str) -> None:
        """
        Create stream + consumer group if missing.

        Redis commands:
            XGROUP CREATE <stream> <group> $ MKSTREAM
        """
        key = self.key(channel_id)
        # IDs: "0" (all messages), "$" (only new), specific ID
        # "0" means start consuming from the beginning of the stream
        # "$" means start consuming from new messages only (not historical)
        stream_id = "0" if self.stream_id_type == "stream_from_beginning" else "$"
        try:
            # MKSTREAM will create the stream if it doesn't exist
            await self.r.xgroup_create(key, self.group, id=stream_id, mkstream=True)  # type: ignore[no-untyped-call]
            logger.debug(f"Created consumer group '{self.group}' for stream '{key}'")
        except Exception as e:
            error_msg = str(e)
            # Group already exists -> ignore
            if "BUSYGROUP" in error_msg:
                return
            # Other safe errors to ignore
            if "NOGROUP" in error_msg:
                return
            logger.warning(f"Error creating consumer group for '{key}': {error_msg}")

    # -------------------- producers --------------------
    async def send(self, channel_id: str, data: dict[str, Any]) -> str:
        """
        Send a message to the channel.

        Redis commands:
            XADD <stream> MAXLEN ~ <maxlen> * data <json>
            EXPIRE <stream> <ttl>

        Args:
            channel_id: channel identifier
            data: message payload (will be JSON-encoded)

        Returns:
            message ID (e.g. "1763006032172-0")

        Example:
            msg_id = await mq.send("channel-1", {
                "sender": "alice",
                "text": "hello world",
                "type": "message"
            })
        """
        key = self.key(channel_id)
        await self.ensure_group(channel_id)

        # OPTIMIZATION: Use pipeline to batch XADD and EXPIRE commands
        pipe = self.r.pipeline()  # type: ignore[no-untyped-call]
        pipe.xadd(key, self._encode_payload(data), maxlen=self.maxlen, approximate=True)  # type: ignore[no-untyped-call]
        pipe.expire(key, self.ttl)  # type: ignore[no-untyped-call]
        results = await pipe.execute()  # type: ignore[no-untyped-call]

        msg_id = str(results[0])  # type: ignore[arg-type]
        logger.debug(f"Sent message to '{key}': {msg_id}")
        return msg_id

    async def broadcast(self, channel_id: str, event_type: str, payload: dict[str, Any]) -> str:
        """
        Broadcast an event to all consumers in the channel.

        This is a convenience method that wraps send() with a standard event structure.

        Args:
            channel_id: channel identifier
            event_type: event type (e.g. "message", "notification", "system")
            payload: event payload

        Returns:
            message ID

        Example:
            await mq.broadcast("channel-1", "notification", {
                "title": "New user joined",
                "user": "bob"
            })
        """
        data = {"type": event_type, "payload": payload}
        return await self.send(channel_id, data)

    # -------------------- consumers --------------------
    async def consume(
        self,
        channel_id: str,
        consumer_id: str | None = None,
        *,
        block_ms: int | None = None,
        count: int | None = None,
        stream_method: Literal["new_messages_only", "pending_messages"] = "new_messages_only",
        auto_ack: bool = True,
    ) -> AsyncGenerator[tuple[str, dict[str, Any]]]:
        """
        Consume messages from the channel using consumer groups.

        Redis commands:
            XREADGROUP GROUP <group> <consumer> BLOCK <ms> COUNT <n> STREAMS <stream> >
            XACK <stream> <group> <msg_id> (if auto_ack=True)

        Args:
            channel_id: channel identifier
            consumer_id: unique consumer identifier (auto-generated if None)
            block_ms: blocking time in milliseconds (default: self.block_ms)
            count: number of messages to read per call (default: self.read_count)
            stream_method: "new_messages_only" (>) or "pending_messages" (0)
            auto_ack: if True, acknowledge messages after yielding (default: True)

        Yields:
            (msg_id, payload) tuples

        Example:
            async for msg_id, data in mq.consume("channel-1", "consumer-alice"):
                print(f"Received: {data}")
                # Message is auto-acknowledged
        """
        key = self.key(channel_id)
        consumer = consumer_id or str(uuid7())
        block = block_ms or self.block_ms
        read_count = count or self.read_count

        await self.ensure_group(channel_id)

        logger.debug(f"Consumer '{consumer}' started consuming from '{key}'")

        try:
            while True:
                try:
                    # Read new messages for this consumer group
                    # ">" means only new undelivered messages
                    # "0" means pending messages (delivered but not acknowledged)
                    resp = await self.r.xreadgroup(  # type: ignore[no-untyped-call]
                        groupname=self.group,
                        consumername=consumer,
                        streams={key: ">" if stream_method == "new_messages_only" else "0"},
                        count=read_count,
                        block=block,
                    )
                except Exception as e:
                    logger.error(f"Error reading from stream '{key}': {e}")
                    await asyncio.sleep(1.0)
                    continue

                if not resp:
                    # No messages, continue blocking
                    continue

                # resp is a list of (stream, [(id, {field: value}), ...])
                for _stream, messages in resp:  # type: ignore[misc]
                    for msg_id, fields in messages:  # type: ignore[misc]
                        payload = self._decode_payload(fields)  # type: ignore[arg-type]

                        # Yield message to consumer
                        yield msg_id, payload  # type: ignore[misc]

                        # Acknowledge message if auto_ack is enabled
                        if auto_ack:
                            with suppress(Exception):
                                await self.r.xack(key, self.group, msg_id)  # type: ignore[no-untyped-call]
                                logger.debug(f"Acknowledged message '{msg_id}' from '{key}'")

        finally:
            # Cleanup: remove consumer from group on disconnect
            with suppress(Exception):
                await self.r.xgroup_delconsumer(key, self.group, consumer)  # type: ignore[no-untyped-call]
                logger.debug(f"Removed consumer '{consumer}' from '{key}'")

    async def consume_with_disconnect_check(
        self,
        channel_id: str,
        consumer_id: str | None = None,
        *,
        disconnect_check: Any = None,
        block_ms: int | None = None,
        count: int | None = None,
        stream_method: Literal["new_messages_only", "pending_messages"] = "new_messages_only",
        auto_ack: bool = True,
    ) -> AsyncGenerator[tuple[str, dict[str, Any]]]:
        """
        Consume messages with periodic disconnect checks (for SSE/WebSocket).

        This is useful for FastAPI Request.is_disconnected() checks.

        Args:
            channel_id: channel identifier
            consumer_id: unique consumer identifier (auto-generated if None)
            disconnect_check: async callable that returns True if disconnected
            block_ms: blocking time in milliseconds (default: self.block_ms)
            count: number of messages to read per call (default: self.read_count)
            auto_ack: if True, acknowledge messages after yielding

        Yields:
            (msg_id, payload) tuples

        Example:
            async def is_disconnected():
                return await request.is_disconnected()

            async for msg_id, data in mq.consume_with_disconnect_check(
                "channel-1", "consumer-alice", disconnect_check=is_disconnected
            ):
                print(f"Received: {data}")
        """
        key = self.key(channel_id)
        consumer = consumer_id or str(uuid7())
        block = block_ms or self.block_ms
        read_count = count or self.read_count

        await self.ensure_group(channel_id)

        logger.debug(f"Consumer '{consumer}' started consuming from '{key}' with disconnect check")

        try:
            while True:
                # Check if client disconnected
                if disconnect_check is not None:
                    if callable(disconnect_check):
                        is_disconnected = (
                            await disconnect_check()
                            if asyncio.iscoroutinefunction(disconnect_check)
                            else disconnect_check()
                        )
                        if is_disconnected:
                            logger.debug(f"Client disconnected, stopping consumer '{consumer}'")
                            break

                try:
                    resp = await self.r.xreadgroup(  # type: ignore[no-untyped-call]
                        groupname=self.group,
                        consumername=consumer,
                        # Special IDs:
                        #   ">" : Only new messages never delivered to any consumer
                        #   "0" : Pending messages (delivered but not acknowledged)
                        streams={key: ">" if stream_method == "new_messages_only" else "0"},
                        count=read_count,
                        block=block,
                    )
                except Exception as e:
                    logger.error(f"Error reading from stream '{key}': {e}")
                    await asyncio.sleep(1.0)
                    continue

                if not resp:
                    continue

                for _stream, messages in resp:  # type: ignore[misc]
                    for msg_id, fields in messages:  # type: ignore[misc]
                        payload = self._decode_payload(fields)  # type: ignore[arg-type]
                        yield msg_id, payload  # type: ignore[misc]

                        if auto_ack:
                            with suppress(Exception):
                                await self.r.xack(key, self.group, msg_id)  # type: ignore[no-untyped-call]

        finally:
            with suppress(Exception):
                await self.r.xgroup_delconsumer(key, self.group, consumer)  # type: ignore[no-untyped-call]
                logger.debug(f"Removed consumer '{consumer}' from '{key}'")

    # -------------------- management helpers --------------------
    async def length(self, channel_id: str) -> int:
        """Get stream length. Redis command: XLEN <stream>"""
        return await self.r.xlen(self.key(channel_id))  # type: ignore[no-untyped-call, no-any-return]

    async def pending_count(self, channel_id: str, consumer_id: str | None = None) -> int:
        """
        Get count of pending (unacknowledged) messages.

        Redis command: XPENDING <stream> <group> [<consumer>]

        Args:
            channel_id: channel identifier
            consumer_id: specific consumer (None for all consumers)

        Returns:
            number of pending messages
        """
        key = self.key(channel_id)
        try:
            if consumer_id:
                # TODO: Implement consumer-specific pending count
                # Need to parse XPENDING output for specific consumer
                return 0
            else:
                # Get overall pending count
                pending = await self.r.xpending(key, self.group)  # type: ignore[no-untyped-call]
                return pending["pending"] if pending else 0  # type: ignore[no-any-return]
        except Exception as e:
            logger.warning(f"Error getting pending count for '{key}': {e}")
            return 0

    async def claim_pending(
        self, channel_id: str, consumer_id: str, min_idle_ms: int = 60000, count: int = 10
    ) -> list[tuple[str, dict[str, Any]]]:
        """
        Claim pending messages from other consumers (for failure recovery).

        Redis command: XAUTOCLAIM <stream> <group> <consumer> <min-idle-time> <start>

        Args:
            channel_id: channel identifier
            consumer_id: consumer claiming the messages
            min_idle_ms: minimum idle time in milliseconds (default 60s)
            count: number of messages to claim

        Returns:
            list of (msg_id, payload) tuples

        Example:
            # Claim messages idle for more than 60 seconds
            claimed = await mq.claim_pending("channel-1", "consumer-alice", min_idle_ms=60000)
        """
        key = self.key(channel_id)
        try:
            # XAUTOCLAIM returns (next_id, [(msg_id, fields), ...])
            # TODO: Implement XAUTOCLAIM when available in redis-py
            # For now, use XPENDING + XCLAIM
            logger.warning(f"claim_pending not fully implemented for '{key}'")
            return []
        except Exception as e:
            logger.error(f"Error claiming pending messages from '{key}': {e}")
            return []

    async def trim(self, channel_id: str, maxlen: int, approximate: bool = True) -> int:
        """Trim stream to maxlen. Redis command: XTRIM <stream> MAXLEN ~ <maxlen>"""
        return await self.r.xtrim(self.key(channel_id), maxlen=maxlen, approximate=approximate)  # type: ignore[no-untyped-call, no-any-return]

    async def expire(self, channel_id: str, ttl_seconds: int) -> bool:
        """Set TTL on stream. Redis command: EXPIRE <stream> <ttl>"""
        return await self.r.expire(self.key(channel_id), ttl_seconds)  # type: ignore[no-untyped-call, no-any-return]

    async def delete(self, channel_id: str) -> int:
        """Delete stream. Redis command: DEL <stream>"""
        return await self.r.delete(self.key(channel_id))  # type: ignore[no-untyped-call, no-any-return]

    async def delete_consumer(self, channel_id: str, consumer_id: str) -> int:
        """
        Delete a consumer from the consumer group.

        Redis command: XGROUP DELCONSUMER <stream> <group> <consumer>
        """
        key = self.key(channel_id)
        try:
            return await self.r.xgroup_delconsumer(key, self.group, consumer_id)  # type: ignore[no-untyped-call, no-any-return]
        except Exception as e:
            logger.warning(f"Error deleting consumer '{consumer_id}' from '{key}': {e}")
            return 0

    async def info(self, channel_id: str) -> dict[str, Any]:
        """
        Get stream info.

        Redis command: XINFO STREAM <stream>

        Returns:
            stream information dict
        """
        key = self.key(channel_id)
        try:
            return await self.r.xinfo_stream(key)  # type: ignore[no-untyped-call, no-any-return]
        except Exception as e:
            logger.warning(f"Error getting stream info for '{key}': {e}")
            return {}

    async def group_info(self, channel_id: str) -> list[dict[str, Any]]:
        """
        Get consumer group info.

        Redis command: XINFO GROUPS <stream>

        Returns:
            list of consumer group information dicts
        """
        key = self.key(channel_id)
        try:
            return await self.r.xinfo_groups(key)  # type: ignore[no-untyped-call, no-any-return]
        except Exception as e:
            logger.warning(f"Error getting group info for '{key}': {e}")
            return []

    async def consumers_info(self, channel_id: str) -> list[dict[str, Any]]:
        """
        Get consumers info for the consumer group.

        Redis command: XINFO CONSUMERS <stream> <group>

        Returns:
            list of consumer information dicts
        """
        key = self.key(channel_id)
        try:
            return await self.r.xinfo_consumers(key, self.group)  # type: ignore[no-untyped-call, no-any-return]
        except Exception as e:
            logger.warning(f"Error getting consumers info for '{key}': {e}")
            return []


# ---------------------------------------------------------------------------
# SSE helper
# ---------------------------------------------------------------------------


async def sse_event(data: dict[str, Any], event: str | None = None) -> bytes:
    """
    Encode dict as SSE (Server-Sent Events) format.

    Args:
        data: payload to send
        event: optional event type

    Returns:
        SSE-formatted bytes

    Example:
        yield await sse_event({"type": "message", "text": "hello"}, event="message")
    """
    # OPTIMIZATION: Compact JSON with separators=(",", ":")
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    lines: list[str] = []
    if event:
        lines.append(f"event: {event}\n")
    for chunk in payload.splitlines() or [payload]:
        lines.append(f"data: {chunk}\n")
    lines.append("\n")
    return "".join(lines).encode("utf-8")


# ---------------------------------------------------------------------------
# Usage examples
# ---------------------------------------------------------------------------


async def example_producer(channel_id: str, sender: str = "alice", count: int = 10) -> None:
    """Example producer that sends messages to a channel."""

    logger.info(f"Starting producer for channel: {channel_id}, sender: {sender}")

    try:
        mq = RedisStreamMessageQueue()

        for i in range(1, count + 1):
            msg_id = await mq.send(
                channel_id,
                {
                    "sender": sender,
                    "text": f"Message {i} from {sender}",
                    "type": "message",
                },
            )
            logger.info(f"Sent message {i}: {msg_id}")
            await asyncio.sleep(0.5)

        # Send completion marker
        await mq.send(channel_id, {"type": "done", "sender": sender})
        logger.info(f"Producer finished for channel: {channel_id}")

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        raise


async def example_consumer(channel_id: str, consumer_id: str = "consumer-1") -> None:
    """Example consumer that receives messages from a channel."""

    logger.info(f"Starting consumer: {consumer_id} for channel: {channel_id}")

    try:
        mq = RedisStreamMessageQueue()

        async for msg_id, data in mq.consume(channel_id, consumer_id):
            logger.info(f"Received: {msg_id} -> {data}")

            # Stop if done marker is received
            if data.get("type") == "done":
                logger.info("Done marker received, stopping consumer")
                break

        logger.info(f"Consumer finished for channel: {channel_id}")

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        raise


async def example_sse_stream(channel_id: str, consumer_id: str | None = None) -> AsyncGenerator[bytes]:
    """
    Example SSE stream generator for FastAPI StreamingResponse.

    Usage:
        @app.get("/channels/{channel_id}/events")
        async def sse_endpoint(channel_id: str):
            return StreamingResponse(
                example_sse_stream(channel_id),
                media_type="text/event-stream"
            )
    """

    logger.info(f"Starting SSE stream for channel: {channel_id}")

    try:
        mq = RedisStreamMessageQueue()
        consumer = consumer_id or str(uuid7())

        # Send initial connection message
        yield await sse_event({"type": "connected", "consumer": consumer}, event="system")

        async for msg_id, data in mq.consume(channel_id, consumer):
            logger.info(f"Streaming: {msg_id} -> {data}")

            # Build SSE payload
            payload = {
                "id": msg_id,
                "type": data.get("type", "message"),
                "data": data,
                "ts": int(msg_id.split("-")[0]),
            }

            # Yield as SSE event
            yield await sse_event(payload, event=data.get("type", "message"))

            # Stop if done marker
            if data.get("type") == "done":
                logger.info("Done marker received, closing stream")
                break

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        yield await sse_event({"type": "error", "message": str(e)}, event="error")

    finally:
        logger.info(f"SSE stream closed for channel: {channel_id}")


# ---------------------------------------------------------------------------
# Quick Reference Guide
# ---------------------------------------------------------------------------
"""
QUICK REFERENCE GUIDE
=====================

1. BASIC PRODUCER (Send messages)
   -------------------------------
   from app.core.rsmqueue import RedisStreamMessageQueue

   mq = RedisStreamMessageQueue()
   msg_id = await mq.send("channel-1", {
       "sender": "alice",
       "text": "hello world",
       "type": "message"
   })


2. BASIC CONSUMER (Receive messages)
   ----------------------------------
   from app.core.rsmqueue import RedisStreamMessageQueue

   mq = RedisStreamMessageQueue()
   async for msg_id, data in mq.consume("channel-1", "consumer-alice"):
       print(f"Received: {data}")
       # Message is auto-acknowledged


3. SSE ENDPOINT (FastAPI)
   -----------------------
   from fastapi import APIRouter, Request
   from fastapi.responses import StreamingResponse
   from app.core.rsmqueue import RedisStreamMessageQueue, sse_event

   @app.get("/channels/{channel_id}/events")
   async def sse_endpoint(channel_id: str, request: Request):
       mq = RedisStreamMessageQueue()

       async def stream():
           async for msg_id, data in mq.consume_with_disconnect_check(
               channel_id, disconnect_check=request.is_disconnected
           ):
               yield await sse_event(data, event="message")

       return StreamingResponse(
           stream(),
           media_type="text/event-stream"
       )


4. BROADCAST EVENT
   ----------------
   mq = RedisStreamMessageQueue()
   await mq.broadcast("channel-1", "notification", {
       "title": "New user joined",
       "user": "bob"
   })


5. MANAGEMENT OPERATIONS
   ----------------------
   mq = RedisStreamMessageQueue()

   # Get stream info
   info = await mq.info("channel-1")

   # Get consumer group info
   groups = await mq.group_info("channel-1")

   # Get active consumers
   consumers = await mq.consumers_info("channel-1")

   # Get stream length
   length = await mq.length("channel-1")

   # Delete channel
   await mq.delete("channel-1")


6. CURL EXAMPLES
   --------------
   # Send message
   curl -X POST http://localhost:33001/api/v1/mq/channels/general/messages \
     -H "Content-Type: application/json" \
     -d '{"sender":"alice","text":"hello world"}'

   # Subscribe to events (SSE)
   curl -N http://localhost:33001/api/v1/mq/channels/general/events

   # Get channel info
   curl http://localhost:33001/api/v1/mq/channels/general/info


7. REDIS COMMANDS USED
   --------------------
   - XADD: Add message to stream
   - XREADGROUP: Read messages with consumer group
   - XACK: Acknowledge message processing
   - XGROUP CREATE: Create consumer group
   - XGROUP DELCONSUMER: Remove consumer from group
   - XLEN: Get stream length
   - XTRIM: Trim stream to max length
   - XINFO STREAM: Get stream information
   - XINFO GROUPS: Get consumer group information
   - XINFO CONSUMERS: Get consumer information
   - XPENDING: Get pending messages
   - EXPIRE: Set TTL on stream
   - DEL: Delete stream


8. CONFIGURATION
   --------------
   RedisStreamMessageQueue(
       redis_url="redis://localhost:6379/0",  # Redis connection URL
       stream_prefix="mq:channel:",           # Stream key prefix
       consumer_group="mq-consumer-default",  # Consumer group name
       maxlen=10000,                          # Max messages per stream
       ttl_seconds=86400,                     # Stream TTL (24h)
       block_ms=15000,                        # Blocking read timeout (15s)
       read_count=10,                         # Messages per read
   )
"""
