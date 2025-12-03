"""
AI service endpoints

Integration with hm-aurorah-lang AI agent service
"""

from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.services.langgraph_client import langgraph_client

router = APIRouter()


class TranslationRequest(BaseModel):
    """Translation request model"""

    text: str
    source_language: str = "en"
    target_language: str = "es"


class AnalysisRequest(BaseModel):
    """Text analysis request model"""

    text: str


class TaskRequest(BaseModel):
    """Generic task request model"""

    task_type: str
    data: dict[str, Any]


@router.post("/translate")
async def translate_text(request: TranslationRequest) -> dict[str, Any]:
    """
    Translate text using AI translation service

    Args:
        request: Translation request

    Returns:
        Translation result
    """
    try:
        result = await langgraph_client.translate_text(
            text=request.text,
            source_language=request.source_language,
            target_language=request.target_language,
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Translation service error: {str(e)}",
        )


@router.post("/analyze")
async def analyze_text(request: AnalysisRequest) -> dict[str, Any]:
    """
    Analyze text using AI analysis service

    Args:
        request: Analysis request

    Returns:
        Analysis result
    """
    try:
        result = await langgraph_client.analyze_text(text=request.text)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Analysis service error: {str(e)}",
        )


@router.post("/tasks")
async def process_task(request: TaskRequest) -> dict[str, Any]:
    """
    Process a task using AI agent service

    Args:
        request: Task request

    Returns:
        Task processing result
    """
    try:
        result = await langgraph_client.process_task(
            task_type=request.task_type,
            task_data=request.data,
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Task processing error: {str(e)}",
        )


@router.get("/health")
async def check_ai_service_health() -> dict[str, Any]:
    """
    Check AI service health status

    Returns:
        Health status
    """
    is_healthy = await langgraph_client.health_check()

    if is_healthy:
        return {
            "status": "healthy",
            "service": "hm-aurorah-lang",
            "available": True,
        }
    else:
        return {
            "status": "unhealthy",
            "service": "hm-aurorah-lang",
            "available": False,
        }
