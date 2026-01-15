"""
File checkpoint model

SQL Function                    Model Schema
------------------------------  ----------------------------------------------
au_create_file_checkpoint       FileCheckpointCreate, FileCheckpointCreateResponse
au_get_file_checkpoint          FileCheckpointRead

See: scripts/schema-functions/schema-public.file.checkpoint.sql
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Column, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel  # type: ignore[attr-defined]
from uuid_utils import uuid7


class FileCheckpointBase(SQLModel):
    """Base file checkpoint model"""

    file_id: uuid.UUID = Field(foreign_key="public.au_file_nodes.file_id", index=True)
    history_id: uuid.UUID = Field(foreign_key="public.au_file_edit_history.history_id", index=True)
    original_text_modified: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))
    translated_text_modified: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))
    proofreaded_text: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))


class FileCheckpoint(FileCheckpointBase, table=True):
    """File checkpoint database model"""

    __tablename__ = "au_file_checkpoint"  # type: ignore[assignment]
    __table_args__ = {"schema": "public"}

    checkpoint_id: uuid.UUID = Field(default_factory=uuid7, primary_key=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True)),
    )


class FileCheckpointCreate(SQLModel):
    """Schema for creating a file checkpoint"""

    file_id: uuid.UUID
    history_id: uuid.UUID
    original_text_modified: dict[str, Any] | None = None
    translated_text_modified: dict[str, Any] | None = None
    proofreaded_text: dict[str, Any] | None = None


class FileCheckpointCreateResponse(SQLModel):
    """Schema for creating a file checkpoint response"""

    checkpoint_id: uuid.UUID


class FileCheckpointRead(FileCheckpointBase):
    """Schema for reading a file checkpoint"""

    checkpoint_id: uuid.UUID
    created_at: datetime
