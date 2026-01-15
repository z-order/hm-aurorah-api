"""
API v1 main router
"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    chatbot,
    chatbot_stream,
    file_acl,
    file_check_point,
    file_edit_history,
    file_node,
    file_original,
    file_preset,
    file_proofreading,
    file_task,
    file_translation,
    message_queue,
)

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(file_node.router, prefix="/file/node", tags=["File Node"])
api_router.include_router(file_acl.router, prefix="/file/acl", tags=["File ACL"])
api_router.include_router(file_check_point.router, prefix="/file/checkpoint", tags=["File Checkpoint"])
api_router.include_router(file_edit_history.router, prefix="/file/edit-history", tags=["File Edit History"])
api_router.include_router(file_original.router, prefix="/file/original", tags=["File Original"])
api_router.include_router(file_preset.router, prefix="/file/preset", tags=["File Preset"])
api_router.include_router(file_proofreading.router, prefix="/file/proofreading", tags=["File Proofreading"])
api_router.include_router(file_task.router, prefix="/file/task", tags=["File Task"])
api_router.include_router(file_translation.router, prefix="/file/translation", tags=["File Translation"])
api_router.include_router(chatbot.router, prefix="/chatbot", tags=["Chatbot"])
api_router.include_router(chatbot_stream.router, prefix="/chatbot-stream", tags=["Chatbot Stream"])
api_router.include_router(message_queue.router, prefix="/mq", tags=["Message Queue"])
