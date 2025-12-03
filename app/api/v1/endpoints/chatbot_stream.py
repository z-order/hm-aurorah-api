"""
AI Chatbot endpoints
"""

import logging

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from starlette.responses import JSONResponse

from app.core.logger import get_logger
from app.core.rsbuffer import example_rsbuf_endpoint_poc, example_rsbuf_stream_sse

router: APIRouter = APIRouter()

logger = get_logger(__name__, logging.INFO)


"""
This is the architecture of the chatbot streaming messages by using SSE (Server-Sent Events).

    Web Browser (Next.js)        Python FastAPI server            LangGraph API Server
            |                              |                               |
        Post Action      ---->   client.runs.stream() call   ---->  LLM calls and streaming start
            |                              |                               |
   Get the Post results  <----   Send result of Action                     |
            |                              |                               |
            |                 1) Stream chunk to Cache       <----   Streaming chunk messages
            |                 2) Each chunk has SeqNo                      |
            |                 3) If the client is connected relay stream to client
            |                              |                               |
        SSE Client       ---->        SSE Server                           |
        SSE Client       <----  Streaming chunk messages     <----   Streaming chunk messages (No.1 ~ No.100)
 (From chunk No.1 ~ No.100)         (No.101 ~ No.200)                      |
            |                              |                               |
  [Display streaming text]                 |                               |
            |                              |                               |
  Client Browser Refresh                   |                               |
            |                              |                               |
            |                         SSE Server                           |
            |                   Streaming chunk messages     <----   Streaming chunk messages (No.101 ~ No.200)
            |                       (No.101 ~ No.200)                      |
            |                              |                               |
        Post Action      ---->   Check streaming status      <----   Streaming chunk messages (No.201 ~ No.300)
     [Client Refresh]                      |                               |
            |                              |                               |
   Get the Post results  <----   Send result of Action       <----   Streaming chunk messages (No.301 ~ No.400)
 (From chunk No.1 ~ No.400)                |                               |
            |                              |                               |
        SSE Client       ---->        SSE Server                           |
        SSE Client       <----  Streaming chunk messages     <----   Streaming chunk messages (No.401 ~ No.500)
 (From chunk No.401 ~ No.500)       (No.401 ~ No.500)                      |
            |                              |                               |
        SSE Client       <----  Final Streaming chunk messages             |
            |                              |                               |
    [Display final result]                 |                               |
"""


@router.get("/rsbuf-poc", summary="RedisStreamBuffer - POC", include_in_schema=False)
async def rsbuf_poc() -> JSONResponse:
    """
    RedisStreamBuffer - POC (Proof of Concept)
    """
    logger.info("Starting RedisStreamBuffer examples")
    return JSONResponse(content=await example_rsbuf_endpoint_poc())


@router.get("/rsbuf-sse/{run_id}", summary="RedisStreamBuffer - SSE", include_in_schema=False)
async def rsbuf_sse(run_id: str) -> StreamingResponse:
    """
    RedisStreamBuffer - SSE (Server-Sent Events)
    """
    logger.info(f"Starting RedisStreamBuffer stream for run_id: {run_id}")
    return StreamingResponse(example_rsbuf_stream_sse(run_id), media_type="text/event-stream")
