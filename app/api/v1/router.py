"""
API v1 main router
"""

from fastapi import APIRouter

from app.api.v1.endpoints import chatbot, chatbot_stream, file_node, message_queue

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(file_node.router, prefix="/file/node", tags=["File Node"])
api_router.include_router(chatbot.router, prefix="/chatbot", tags=["Chatbot"])
api_router.include_router(chatbot_stream.router, prefix="/chatbot-stream", tags=["Chatbot Stream"])
api_router.include_router(message_queue.router, prefix="/mq", tags=["Message Queue"])
