"""
Message Queue endpoints using Redis Streams
"""

import logging
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from uuid_utils import uuid7

from app.core.logger import get_logger
from app.core.rsmqueue import RedisStreamMessageQueue, example_sse_stream, sse_event

router: APIRouter = APIRouter()

logger = get_logger(__name__, logging.INFO)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class MessageIn(BaseModel):
    """Incoming message payload"""

    sender: str = Field(..., examples=["alice"])
    text: str = Field(..., examples=["hello world"])
    client_id: str | None = Field(None, examples=["550e8400-e29b-41d4-a716-446655440000"])


class MessageOut(BaseModel):
    """Outgoing message response"""

    id: str
    sender: str
    text: str
    ts: int


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/channels/{channel_id}/messages", response_model=MessageOut, summary="Send message to channel")
async def send_message_to_channel(channel_id: str, payload: MessageIn) -> MessageOut:
    """
    Send a message to a channel.

    The message will be broadcast to all consumers listening to this channel.

    Args:

        - channel_id: channel identifier
        - payload: message payload

    Returns: Message information with ID and timestamp
    """

    try:
        mq = RedisStreamMessageQueue()

        # Build message data
        data = {
            "sender": payload.sender,
            "text": payload.text,
            "type": "message",
        }
        if payload.client_id:
            data["client_id"] = payload.client_id

        # Send message to Redis Stream
        msg_id = await mq.send(channel_id, data)

        # Extract timestamp from message ID
        ts = int(msg_id.split("-")[0])

        logger.info(f"Sent message to channel '{channel_id}': {msg_id}")

        return MessageOut(
            id=msg_id,
            sender=payload.sender,
            text=payload.text,
            ts=ts,
        )

    except Exception as e:
        logger.error(f"Error sending message: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to send message: {str(e)}")


@router.get("/channels/{channel_id}/events", summary="Subscribe to channel events (SSE)")
async def subscribe_to_channel_events(
    channel_id: str,
    request: Request,
    method: Literal["s", "n", "p"] = Query(
        "s",
        description="Stream method: (s)tream_from_beginning (default) | (n)ew_messages_only | (p)ending_messages first then new",
    ),
):
    """
    Subscribe to channel events using Server-Sent Events (SSE).

    This endpoint streams messages in real-time to connected clients.
    Each client gets its own consumer ID and receives all new messages.

    Args:

        - channel_id: channel identifier
        - request: FastAPI request object (for disconnect detection)

    Query Parameters:

        - consumer: optional consumer ID (auto-generated if not provided)
        - method: (s)tream_from_beginning (default) | (n)ew_messages_only | (p)ending_messages first then new

    Returns: SSE stream of messages

    Example:

        $ curl -N http://localhost:8000/api/v1/mq/channels/general/events?method=s
    """

    consumer_id = request.query_params.get("consumer") or str(uuid7())

    logger.info(f"Starting SSE stream for channel '{channel_id}', consumer '{consumer_id}'")

    headers = {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache, no-transform",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }

    async def stream_generator():
        """Generator that streams messages with disconnect detection."""
        try:
            # Use unique consumer group per browser for broadcast behavior
            stream_id_type = "stream_from_beginning" if method == "s" else "stream_from_new_only"
            mq = RedisStreamMessageQueue(consumer_group=f"mq-consumer-{consumer_id}", stream_id_type=stream_id_type)

            # Send initial connection event
            yield await sse_event({"type": "connected", "consumer": consumer_id}, event="system")

            # Stream messages with disconnect check
            stream_method = "new_messages_only" if method in ("s", "n") else "pending_messages"
            async for msg_id, data in mq.consume_with_disconnect_check(
                channel_id,
                consumer_id,
                disconnect_check=request.is_disconnected,
                auto_ack=False,
                stream_method=stream_method,
            ):
                # Build SSE payload
                event_type = data.get("type", "message")
                payload = {
                    "id": msg_id,
                    "type": "done" if event_type == "done" else "data",
                    "data": data,
                    "ts": int(msg_id.split("-")[0]),
                    "channel": channel_id,
                }

                # Yield as SSE event (system events like "done" use event: system)
                sse_event_name = "system" if event_type == "done" else event_type
                yield await sse_event(payload, event=sse_event_name)

                # Stop if done marker
                if event_type == "done":
                    logger.info(f"Done marker received for channel '{channel_id}'")
                    break

        except Exception as e:
            logger.error(f"Error in SSE stream: {e}", exc_info=True)
            yield await sse_event({"type": "error", "message": str(e)}, event="error")

        finally:
            logger.info(f"SSE stream closed for channel '{channel_id}', consumer '{consumer_id}'")

    return StreamingResponse(stream_generator(), headers=headers, status_code=200)


@router.get("/channels/{channel_id}/info", summary="Get channel information")
async def get_channel_info(channel_id: str):
    """
    Get information about a channel.

    Returns stream info, consumer group info, and active consumers.

    Args:

        - channel_id: channel identifier

    Returns: Channel information
    """

    try:
        mq = RedisStreamMessageQueue()

        stream_info = await mq.info(channel_id)
        group_info = await mq.group_info(channel_id)
        consumers_info = await mq.consumers_info(channel_id)
        length = await mq.length(channel_id)

        logger.info(f"Retrieved info for channel '{channel_id}'")

        return JSONResponse(
            content={
                "channel_id": channel_id,
                "length": length,
                "stream_info": stream_info,
                "group_info": group_info,
                "consumers": consumers_info,
            }
        )

    except Exception as e:
        logger.error(f"Error getting channel info: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get channel info: {str(e)}")


@router.delete("/channels/{channel_id}", summary="Delete channel")
async def delete_channel(channel_id: str):
    """
    Delete a channel and all its messages.

    Args:

        - channel_id: channel identifier

    Returns: Deletion confirmation
    """

    try:
        mq = RedisStreamMessageQueue()
        deleted = await mq.delete(channel_id)

        logger.info(f"Deleted channel '{channel_id}': {deleted} keys removed")

        return JSONResponse(content={"channel_id": channel_id, "deleted": deleted > 0})

    except Exception as e:
        logger.error(f"Error deleting channel: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete channel: {str(e)}")


# ---------------------------------------------------------------------------
# Example/Demo endpoints
# ---------------------------------------------------------------------------


@router.get("/example/sse/{channel_id}", summary="Example SSE stream", include_in_schema=False)
async def example_sse_channel(channel_id: str):
    """
    Example SSE stream endpoint (for testing).

    This uses the example_sse_stream generator from rsmqueue.
    """

    logger.info(f"Starting example SSE stream for channel '{channel_id}'")

    headers = {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache, no-transform",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }

    return StreamingResponse(example_sse_stream(channel_id), headers=headers, status_code=200)


@router.get("/", summary="Message Queue API info")
async def index():
    """
    Get API information and usage examples.

    Name: Message Queue API

    Description: Redis Stream-based message queue for chat and events

    Send message example:

        $ curl -X POST http://localhost:8000/api/v1/mq/channels/general/messages -H "Content-Type: application/json" -H "Authorization: Bearer $API_KEY" -d '{"sender":"alice","text":"hello world"}'

    Subscribe to events example:

        $ curl -H "Authorization: Bearer $API_KEY" -N http://localhost:8000/api/v1/mq/channels/general/events

    Get channel info example:

        $ curl -H "Authorization: Bearer $API_KEY" http://localhost:8000/api/v1/mq/channels/general/info

    Returns: API information and usage examples
    """
    return JSONResponse(
        content={
            "name": "Message Queue API",
            "description": "Redis Stream-based message queue for chat and events",
            "examples": {
                "send_message": "$ curl -X POST http://localhost:8000/api/v1/mq/channels/general/messages "
                '-H "Content-Type: application/json" '
                '-H "Authorization: Bearer $API_KEY" '
                '-d \'{"sender":"alice","text":"hello world"}\'',
                "subscribe_sse": '$ curl -H "Authorization: Bearer $API_KEY" -N http://localhost:8000/api/v1/mq/channels/general/events',
                "channel_info": '$ curl -H "Authorization: Bearer $API_KEY" http://localhost:8000/api/v1/mq/channels/general/info',
            },
        }
    )
