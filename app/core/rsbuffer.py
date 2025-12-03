"""
Redis Stream Buffer - rsbuffer.py
----------------------
Reusable Redis-based stream buffer for chunked streaming (e.g., chat or SSE systems).

This module abstracts the "in-memory ring buffer" concept into Redis Streams, making it usable
across multiple processes or servers. It provides convenient methods for appending, reading,
backfilling, trimming, and TTL-based cleanup.

Includes working async usage examples for producers and consumers (no SSE required).

OPTIMIZATIONS APPLIED:
- JSON optimization: Compact JSON output with separators=(",", ":")
- Redis pipeline: Batched XADD and EXPIRE commands to reduce network round-trips
- Code simplification: Ternary operators for cleaner code
- Type hints: TYPE_CHECKING for better IDE support without runtime overhead
- Memory optimization: __slots__ to reduce memory footprint per instance
- Documentation: Enhanced docstrings for clarity
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, Any

from redis import asyncio as aioredis  # type: ignore[import-untyped]

from app.core.config import settings
from app.core.logger import get_logger

# Use uvicorn logger to ensure logs are visible
logger = get_logger(__name__, logging.INFO)

# OPTIMIZATION: TYPE_CHECKING for better IDE support without runtime overhead
if TYPE_CHECKING:
    from redis.asyncio import Redis  # type: ignore[import-untyped]


class RedisStreamBuffer:
    """
    A simple, reusable wrapper around Redis Streams for "append + backfill + tail".

    Redis Keys:
        Each "run" is a Redis Stream: <prefix><run_id>

    Stored entry shape:
        { "data": "<json string>" }

    Typical usage:

        buf = RedisStreamBuffer("redis://localhost")
        await buf.append("run-1", {"text": "chunk"})
        async for id, payload in buf.backfill("run-1", "0-0"):
            print(id, payload)

    Notes on Stream IDs:
        - Stream IDs look like "1716400000000-0" (millisecond timestamp + sequence).
        - You can use "0-0" to read from the beginning, or "$" to wait for new items only.
    """

    # OPTIMIZATION: __slots__ to reduce memory footprint per instance
    __slots__ = ("r", "prefix", "maxlen", "ttl", "block_ms")

    def __init__(
        self,
        redis_url: str | None = None,
        *,
        stream_prefix: str = "rsbuf:",
        maxlen: int = 10000,
        ttl_seconds: int = 3600,  # 1 hour
        block_ms: int = 15000,  # 15 seconds
        decode_responses: bool = True,
    ):
        """
        Args:
            redis_url: e.g. "redis://localhost:6379/0" (defaults to config.redis_url)
            stream_prefix: prefix for stream keys, e.g. "rsbuf:" -> "rsbuf:<run_id>"
            maxlen: number of entries kept per stream (XADD MAXLEN ~)
            ttl_seconds: expiration time (EXPIRE) for each stream
            block_ms: default blocking time for tail() calls
            decode_responses: if True, decode bytes to strings
        """
        url = redis_url or settings.redis_url
        self.r: Redis = aioredis.from_url(url, decode_responses=decode_responses)  # type: ignore[no-untyped-call]
        self.prefix: str = stream_prefix
        self.maxlen: int = maxlen
        self.ttl: int = ttl_seconds
        self.block_ms: int = block_ms

    # -------------------- utilities --------------------
    def key(self, run_id: str) -> str:
        """Generate Redis key for a run ID."""
        return f"{self.prefix}{run_id}"

    @staticmethod
    def _encode_payload(data: dict[str, Any]) -> dict[str, str]:
        """Encode payload data to Redis stream format."""
        # OPTIMIZATION: Compact JSON with separators=(",", ":") - no spaces after separators
        return {"data": json.dumps(data, ensure_ascii=False, separators=(",", ":"))}

    @staticmethod
    def _decode_payload(fields: dict[str, str]) -> dict[str, Any]:
        """Decode Redis stream fields to payload data."""
        return json.loads(fields["data"])

    # -------------------- producers --------------------
    async def append(self, run_id: str, data: dict[str, Any]) -> str:
        """
        Add an entry to the stream.

        Redis command: XADD
        Example:
            XADD rsbuf:123 MAXLEN ~ 1000 * data '{"text":"chunk 1"}'
        """
        key = self.key(run_id)
        # OPTIMIZATION: Use pipeline to batch XADD and EXPIRE commands (reduces network round-trips)
        pipe = self.r.pipeline()  # type: ignore[no-untyped-call]
        pipe.xadd(key, self._encode_payload(data), maxlen=self.maxlen, approximate=True)  # type: ignore[no-untyped-call]
        pipe.expire(key, self.ttl)  # type: ignore[no-untyped-call]
        results = await pipe.execute()  # type: ignore[no-untyped-call]
        # returns the entry ID: e.g. "1763006032172-0" (millisecond timestamp + sequence number)
        return str(results[0])  # type: ignore[arg-type]

    async def finish(self, run_id: str) -> str:
        """Append a final record {"type": "done"} to mark completion."""
        return await self.append(run_id, {"type": "done"})

    # -------------------- consumers --------------------
    async def backfill(
        self, run_id: str, after_id: str = "0-0", *, count: int | None = None
    ) -> AsyncGenerator[tuple[str, dict[str, Any]]]:
        """
        Read entries newer than `after_id`.

        Redis command: XRANGE
        Example:
            XRANGE rsbuf:123 (1700000000000-0 +
        """
        key = self.key(run_id)
        start = f"({after_id}"  # ( means exclusive - exclude this ID (start after 'after_id')
        end = "+"
        if count is None:
            entries = await self.r.xrange(key, min=start, max=end)  # type: ignore[no-untyped-call]
            for eid, fields in entries:  # type: ignore[misc]
                yield eid, self._decode_payload(fields)  # type: ignore[arg-type]
            return

        last = after_id
        while True:
            # ( means exclusive - exclude this ID (start after 'last')
            entries = await self.r.xrange(key, min=f"({last}", max=end, count=count)  # type: ignore[no-untyped-call]
            if not entries:
                break
            for eid, fields in entries:  # type: ignore[misc]
                yield eid, self._decode_payload(fields)  # type: ignore[arg-type]
            # ex) entries = [("1763006032172-0", {"text": "chunk 1"}), ("1763006032172-1", {"text": "chunk 2"})]
            #     -> last = "1763006032172-1" (last entry ID)
            last = entries[-1][0]  # type: ignore[misc]

    async def tail(
        self, run_id: str, after_id: str, *, block_ms: int | None = None
    ) -> AsyncGenerator[tuple[str, dict[str, Any]]]:
        """
        Block and yield new entries.

        Redis command: XREAD
        Example:
            XREAD BLOCK 20000 STREAMS rsbuf:123 1700000000000-0
        """
        key = self.key(run_id)
        block = block_ms or self.block_ms
        last_id = after_id
        while True:
            resp = await self.r.xread({key: last_id}, block=block)  # type: ignore[no-untyped-call]
            if not resp:
                continue
            _, items = resp[0]  # type: ignore[misc]
            for eid, fields in items:  # type: ignore[misc]
                last_id = eid  # type: ignore[misc]
                yield eid, self._decode_payload(fields)  # type: ignore[arg-type]

    # -------------------- management helpers --------------------
    async def length(self, run_id: str) -> int:
        """Get stream length. Redis command: XLEN rsbuf:123"""
        return await self.r.xlen(self.key(run_id))  # type: ignore[no-untyped-call, no-any-return]

    async def last_id(self, run_id: str) -> str | None:
        """Get last entry ID. Redis command: XREVRANGE rsbuf:123 + - COUNT 1"""
        entries = await self.r.xrevrange(self.key(run_id), max="+", min="-", count=1)  # type: ignore[no-untyped-call]
        # OPTIMIZATION: Simplified with ternary operator for cleaner code
        return entries[0][0] if entries else None  # type: ignore[no-any-return]

    async def trim(self, run_id: str, maxlen: int, approximate: bool = True) -> int:
        """Trim stream to maxlen. Redis command: XTRIM rsbuf:123 MAXLEN ~ 5000"""
        return await self.r.xtrim(self.key(run_id), maxlen=maxlen, approximate=approximate)  # type: ignore[no-untyped-call, no-any-return]

    async def expire(self, run_id: str, ttl_seconds: int) -> bool:
        """Set TTL on stream. Redis command: EXPIRE rsbuf:123 900"""
        return await self.r.expire(self.key(run_id), ttl_seconds)  # type: ignore[no-untyped-call, no-any-return]

    async def delete(self, run_id: str) -> int:
        """Delete stream. Redis command: DEL rsbuf:123"""
        return await self.r.delete(self.key(run_id))  # type: ignore[no-untyped-call, no-any-return]

    async def range(
        self, run_id: str, start: str = "-", end: str = "+", count: int | None = None
    ) -> list[tuple[str, dict[str, Any]]]:
        """Read range of entries. Redis command: XRANGE rsbuf:123 - + COUNT 100"""
        entries = await self.r.xrange(self.key(run_id), min=start, max=end, count=count)  # type: ignore[no-untyped-call]
        return [(eid, self._decode_payload(fields)) for eid, fields in entries]  # type: ignore[misc, arg-type]


# ---------------------------------------------------------------------------
# Quick usage examples
# ---------------------------------------------------------------------------


#
# Example for RedisStreamBuffer producer
#
async def example_rsbuf_producer(run_id: str, max_chunks: int = 10) -> None:
    logger.info(f"Starting producer for run ID: {run_id}")
    try:
        # Initialize RedisStreamBuffer with config
        rsbuf: RedisStreamBuffer = RedisStreamBuffer(stream_prefix="rsbuf:", maxlen=1000, ttl_seconds=900)

        # Append 5 chunks to the stream
        for i in range(1, max_chunks):
            eid = await rsbuf.append(run_id, {"text": f"chunk {i}"})
            logger.info(f"rsbuf.append({run_id}, {{'text': 'chunk {i}'}}) -> {eid}")
            await asyncio.sleep(0.5)

        # Mark stream as finished
        await rsbuf.finish(run_id)
        logger.info(f"rsbuf.finish({run_id})")
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        raise


#
# Example for RedisStreamBuffer consumer
#
async def example_rsbuf_consumer(run_id: str) -> None:
    logger.info(f"Starting consumer for run ID: {run_id}")

    try:
        # Initialize RedisStreamBuffer (uses config.redis_url by default)
        rsbuf: RedisStreamBuffer = RedisStreamBuffer()

        last = "0-0"

        # Read existing entries from the stream (backfill)
        async for eid, data in rsbuf.backfill(run_id, after_id=last, count=100):
            logger.info(f"rsbuf.backfill({run_id}, after_id={last}, count=100) -> {eid} {data}")
            last = eid

            # Stop if end marker is found
            if data.get("type") == "done":
                logger.info(f"rsbuf.backfill({run_id}, after_id={last}, count=100) -> DONE seen during backfill")
                return

        # Wait for and read new entries (tail/blocking read)
        logger.info(
            f"rsbuf.tail({run_id}, after_id={last}) -> Waiting for and reading new entries (tail/blocking read)"
        )
        async for eid, data in rsbuf.tail(run_id, after_id=last):
            logger.info(f"rsbuf.tail({run_id}, after_id={last}) -> {eid} {data}")

            # Stop if end marker is found
            if data.get("type") == "done":
                logger.info(f"rsbuf.tail({run_id}, after_id={last}) -> DONE seen during tail")
                return

        logger.info(f"rsbuf.tail({run_id}, after_id={last}) -> Consumer finished")
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        raise


#
# Example endpoint for RedisStreamBuffer for POC (Proof of Concept)
#
async def example_rsbuf_endpoint_poc() -> dict[str, str]:
    """Example endpoint demonstrating RedisStreamBuffer usage for POC (Proof of Concept)."""
    import time

    logger.info("Starting RedisStreamBuffer examples")

    run_id = f"demo-user01-{int(time.time())}"
    logger.info(f"Run ID: {run_id}")

    # Run producer and consumer concurrently without waiting
    task_producer = asyncio.create_task(example_rsbuf_producer(run_id), name="example_rsbuf_producer")
    task_consumer = asyncio.create_task(example_rsbuf_consumer(run_id), name="example_rsbuf_consumer")

    # Add exception handlers to catch errors
    def handle_exception(task: asyncio.Task[None]) -> None:
        try:
            exc = task.exception()
            if exc:
                logger.error(f"Task '{task.get_name()}' failed: {exc}", exc_info=exc)
            else:
                logger.info(f"Task '{task.get_name()}' completed successfully")
        except asyncio.CancelledError:
            logger.warning(f"Task '{task.get_name()}' was cancelled")
        except Exception as e:
            logger.error(f"Error in callback for task '{task.get_name()}': {e}", exc_info=True)

    task_producer.add_done_callback(handle_exception)
    task_consumer.add_done_callback(handle_exception)

    logger.info("Tasks created")

    # Give tasks a moment to start
    await asyncio.sleep(0.2)
    logger.info(f"task_producer done: {task_producer.done()}, task_consumer done: {task_consumer.done()}")

    return {"message": "RedisStreamBuffer producer and consumer examples started. See logs for details."}


#
# Example endpoint for RedisStreamBuffer for SSE (Server-Sent Events)
#
async def example_rsbuf_stream_sse(run_id: str):
    """Async generator that streams RedisStreamBuffer consumer data for StreamingResponse (SSE)."""
    import json

    logger.info(f"Starting RedisStreamBuffer stream for run_id: {run_id}")

    try:
        rsbuf = RedisStreamBuffer()

        # Check if stream already exists (has data)
        stream_exists = False
        async for _ in rsbuf.backfill(run_id, after_id="0-0", count=1):
            stream_exists = True
            break

        # Only start producer if stream doesn't exist
        if not stream_exists:
            logger.info(f"Stream doesn't exist, starting producer for run_id: {run_id}")
            asyncio.create_task(example_rsbuf_producer(run_id, max_chunks=1000), name="example_rsbuf_producer")
        else:
            logger.info(f"Stream already exists, skipping producer for run_id: {run_id}")

        last = "0-0"

        # Read existing entries (backfill)
        logger.info(f"Starting backfill for run_id: {run_id}")
        async for eid, data in rsbuf.backfill(run_id, after_id=last, count=100):
            logger.info(f"Backfill -> {eid} {data}")
            last = eid

            # Yield data as SSE format
            yield f"data: {json.dumps(data)}\n\n"

            # Stop if end marker is found
            if data.get("type") == "done":
                logger.info("DONE seen during backfill")
                return

        # Wait for and read new entries (tail/blocking read)
        logger.info(f"Starting tail for run_id: {run_id}")
        async for eid, data in rsbuf.tail(run_id, after_id=last):
            logger.info(f"Tail -> {eid} {data}")

            # Yield data as SSE format
            yield f"data: {json.dumps(data)}\n\n"

            # Stop if end marker is found
            if data.get("type") == "done":
                logger.info("DONE seen during tail")
                return

        logger.info(f"Stream finished for run_id: {run_id}")

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    finally:
        # Don't cancel producer task - let it continue running for other clients
        # The producer will finish naturally when it completes or when the stream is marked as done
        logger.info(f"Client disconnected for run_id: {run_id}, producer continues in background")
