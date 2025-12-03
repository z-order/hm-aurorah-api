"""
API v1 main router
"""

from fastapi import APIRouter

from app.api.v1.endpoints import ai, auth, chatbot, chatbot_stream, message_queue, projects, tasks, users

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(chatbot.router, prefix="/chatbot", tags=["Chatbot"])
api_router.include_router(chatbot_stream.router, prefix="/chatbot-stream", tags=["Chatbot Stream"])
api_router.include_router(message_queue.router, prefix="/mq", tags=["Message Queue"])
api_router.include_router(auth.router, prefix="/auth", tags=["Samples - Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Samples - Users"])
api_router.include_router(projects.router, prefix="/projects", tags=["Samples - Projects"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["Samples - Tasks"])
api_router.include_router(ai.router, prefix="/ai", tags=["Samples - AI Services"])
