"""
File task model

SQL Function                      Model Schema
--------------------------------  ----------------------------------------------
au_create_file_task               FileTaskCreate
au_update_file_task               FileTaskUpdate
au_get_file_task                  FileTaskRead
au_get_file_task_with_details     FileTaskReadWithDetails

See: scripts/schema-functions/schema-public.file.task.sql
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Column, DateTime
from sqlmodel import Field, SQLModel  # type: ignore[attr-defined]

from app.models.file_node import FileType


class FileTaskBase(SQLModel):
    """Base file task model"""

    file_id: uuid.UUID = Field(foreign_key="public.au_file_nodes.file_id", primary_key=True)
    file_preset_id: uuid.UUID | None = Field(default=None, foreign_key="public.au_file_presets.file_preset_id")
    original_id: uuid.UUID = Field(foreign_key="public.au_file_original.original_id")
    translation_id_1st: uuid.UUID | None = Field(default=None, foreign_key="public.au_file_translation.translation_id")
    translation_id_2nd: uuid.UUID | None = Field(default=None, foreign_key="public.au_file_translation.translation_id")
    proofreading_id: uuid.UUID | None = Field(default=None, foreign_key="public.au_file_proofreading.proofreading_id")


class FileTask(FileTaskBase, table=True):
    """File task database model"""

    __tablename__ = "au_file_tasks"  # type: ignore[assignment]
    __table_args__ = {"schema": "public"}

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True)),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True)),
    )


class FileTaskCreate(SQLModel):
    """Schema for creating a file task"""

    file_id: uuid.UUID
    file_preset_id: uuid.UUID | None = None
    original_text: dict[str, Any]


class FileTaskUpdate(SQLModel):
    """Schema for updating a file task"""

    file_id: uuid.UUID
    file_preset_id: uuid.UUID | None = None
    translation_id_1st: uuid.UUID | None = None
    translation_id_2nd: uuid.UUID | None = None
    proofreading_id: uuid.UUID | None = None


class FileTaskRead(FileTaskBase):
    """Schema for reading a file task"""

    created_at: datetime
    updated_at: datetime


class FileTaskReadWithDetails(SQLModel):
    """Schema for reading a file task with details"""

    file_id: uuid.UUID
    file_preset_id: uuid.UUID | None = None
    original_id: uuid.UUID
    original_text: dict[str, Any] | None = None
    original_text_modified: dict[str, Any] | None = None
    translation_id_1st: uuid.UUID | None = None
    translation_id_2nd: uuid.UUID | None = None
    proofreading_id: uuid.UUID | None = None
    file_type: FileType
    file_name: str
    file_url: str | None = None
    file_ext: str
    file_size: int
    mime_type: str | None = None
    description: str | None = None
    created_at: datetime
    updated_at: datetime
