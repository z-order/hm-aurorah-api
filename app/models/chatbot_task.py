"""
Chatbot task model
"""

import uuid
from datetime import UTC, datetime
from enum import Enum

from sqlalchemy import Column, DateTime, String
from sqlmodel import Field, SQLModel  # type: ignore[attr-defined]
from uuid_utils import uuid7


class ChatbotTaskStatus(str, Enum):
    """Chatbot task status"""

    READY = "ready"  # Task is ready to be started.
    IN_PROGRESS = "in_progress"  # Task is in progress.
    HITL = "hitl"  # Task is in Human-in-the-loop (HITL) mode, waiting for human input.
    COMPLETED = "completed"  # Task was completed successfully.
    FAILED = "failed"  # Task failed due to an error.
    CANCELLED = "cancelled"  # Task was cancelled by the user.
    ABANDONED = "abandoned"  # Task was abandoned by the system.


class ChatbotTaskBase(SQLModel):
    """Base chatbot task model"""

    user_id: str = Field(index=True)  # Foreign key to auth.users.id is managed outside SQLModel.
    name: str = Field(max_length=255, index=True)
    email: str = Field(max_length=255, index=True)
    translation_memory: str | None = Field(default="default-translation-memory", max_length=255)
    translation_role: str | None = Field(default=None)
    thread_id: str = Field(max_length=255)
    title: str = Field(default="New task", max_length=255)
    description: str | None = Field(default=None)
    status: ChatbotTaskStatus = Field(
        default=ChatbotTaskStatus.READY,
        sa_column=Column(String(32)),
    )
    last_run_id: str | None = Field(default=None, max_length=512)  # Foreign key to lang.run.run_id (LangGraph Run ID)


class ChatbotTask(ChatbotTaskBase, table=True):
    """Chatbot task database model"""

    __tablename__ = "au_chatbot_tasks"  # type: ignore[assignment]
    __table_args__ = {"schema": "public"}

    task_id: uuid.UUID = Field(default_factory=uuid7, primary_key=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), index=True),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), index=True),
    )
    deleted_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    is_deleted: bool = Field(default=False, index=True)


class ChatbotTaskCreate(SQLModel):
    """Schema for creating a chatbot task"""

    user_id: str = Field(min_length=4, max_length=255)
    translation_memory: str | None = Field(default="default-translation-memory", min_length=4, max_length=255)
    translation_role: str | None = Field(default=None, max_length=10_000)
    title: str = Field(default="New Task", max_length=255)
    description: str | None = Field(default=None, max_length=4_096)


class ChatbotTaskCreateResponse(SQLModel):
    """Schema for creating a chatbot task response"""

    task_id: uuid.UUID
    thread_id: str


class ChatbotTaskUpdate(SQLModel):
    """Schema for updating a chatbot task"""

    title: str | None = Field(default=None, max_length=255)
    description: str | None = None


class ChatbotTaskRead(ChatbotTaskBase):
    """Schema for reading a task"""

    task_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class ChatbotTaskDelete(SQLModel):
    """Schema for deleting a task"""

    task_id: uuid.UUID
