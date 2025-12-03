"""
Chatbot task model
"""

import uuid
from datetime import UTC, datetime
from enum import Enum

from sqlalchemy import JSON, Column, DateTime
from sqlmodel import Field, SQLModel  # type: ignore[attr-defined]
from uuid_utils import uuid7


class ChatbotMessageStatus(str, Enum):
    """Chatbot message status"""

    PENDING = "pending"  # Message is pending to be processed.
    PROCESSING = "processing"  # Message is being processed.
    HITL = "hitl"  # Message is in Human-in-the-loop (HITL) mode, waiting for human input.
    COMPLETED = "completed"  # Message was completed successfully.
    FAILED = "failed"  # Message failed due to an error.
    CANCELLED = "cancelled"  # Message was cancelled by the user.
    ABANDONED = "abandoned"  # Message was abandoned by the system.


class ChatbotMessageType(str, Enum):
    """Chatbot message type"""

    AI = "ai"
    HUMAN = "human"
    TOOL = "tool"


class ChatbotMessageFile(SQLModel):
    """Chatbot message file model"""

    url: str = Field(max_length=1024)
    name: str = Field(max_length=512)
    mime_type: str = Field(max_length=128)
    extension: str = Field(max_length=16)
    size: int = Field(gt=0, le=1024 * 1024 * 1024 * 2)  # 2GB max size


class ChatbotMessageContent(SQLModel):
    """Chatbot message content model"""

    seqno: int = Field(gt=0, default=1)
    run_id: str = Field(max_length=512)  # Foreign key to lang.runs.run_id (LangGraph Run ID)
    type: ChatbotMessageType = Field(default=ChatbotMessageType.AI)
    # ns_ stands for namespace on LangGraph Namespace Store.
    ns_prefix: str | None = Field(default=None, max_length=512)  # Foreign key to lang.store.prefix
    ns_key: str | None = Field(default=None, max_length=512)  # Foreign key to lang.store.key
    content: str | None = Field(default=None)
    files: list[ChatbotMessageFile] = Field(default_factory=list, min_items=0, max_items=64)


class ChatbotMessageBase(SQLModel):
    """Base chatbot message model"""

    user_id: str = Field(index=True)  # Foreign key to auth.users.id is managed outside SQLModel.
    thread_id: str | None = Field(default=None, max_length=255)
    contents: list[ChatbotMessageContent] = Field(default_factory=list, sa_column=Column(JSON))
    status: ChatbotMessageStatus = Field(default=ChatbotMessageStatus.PENDING)


class ChatbotMessage(ChatbotMessageBase, table=True):
    """Chatbot message database model"""

    __tablename__ = "au_chatbot_messages"  # type: ignore[assignment]
    __table_args__ = {"schema": "public"}

    message_id: uuid.UUID = Field(default_factory=uuid7, primary_key=True)
    task_id: uuid.UUID = Field(foreign_key="public.au_chatbot_tasks.task_id", index=True)
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


class ChatbotMessageCreate(SQLModel):
    """Schema for creating a chatbot message"""

    #
    # Optional parameters for Human-in-the-loop (HITL) mode
    #
    hitl_mode: bool = Field(
        default=False,
        description="Whether to resume the conversation from an existing message in the Human-in-the-loop (HITL) mode, or create a new message",
    )
    hitl_message_id: uuid.UUID | None = Field(
        default=None,
        description="The message ID of the chatbot message to resume the conversation from in the Human-in-the-loop (HITL) mode",
    )

    #
    # Normal mode parameters
    #
    user_id: str = Field(min_length=4, max_length=255)
    task_id: uuid.UUID
    content: str = Field(min_length=1)
    files: list[ChatbotMessageFile] = Field(default_factory=list, min_items=0, max_items=64)


class ChatbotMessageCreateResponse(SQLModel):
    """Schema for creating a chatbot message response"""

    message_id: uuid.UUID


class ChatbotMessageUpdate(SQLModel):
    """Schema for updating a chatbot message"""

    content: str = Field(min_length=1)
    files: list[ChatbotMessageFile] = Field(default_factory=list, min_items=0, max_items=64)


class ChatbotMessageRead(ChatbotMessageBase):
    """Schema for reading a chatbot message"""

    message_id: uuid.UUID
    task_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class ChatbotMessageDelete(SQLModel):
    """Schema for deleting a chatbot message"""

    message_id: uuid.UUID
