"""
File edit history model

SQL Function                      Model Schema
--------------------------------  ----------------------------------------------
au_create_file_edit_history       FileEditHistoryCreate, FileEditHistoryCreateResponse
au_get_file_edit_history          FileEditHistoryRead

See: scripts/schema-functions/schema-public.file.edit-history.sql
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime
from sqlmodel import Field, SQLModel  # type: ignore[attr-defined]
from uuid_utils import uuid7


class FileEditHistoryBase(SQLModel):
    """Base file edit history model"""

    file_id: uuid.UUID = Field(foreign_key="public.au_file_nodes.file_id", index=True)
    target_type: str = Field(max_length=32)  # 'original', 'translation', 'proofreading'
    target_id: uuid.UUID
    marker_number: int
    editor_id: uuid.UUID
    text_before: str | None = Field(default=None)
    text_after: str
    comments: str | None = Field(default=None)


class FileEditHistory(FileEditHistoryBase, table=True):
    """File edit history database model"""

    __tablename__ = "au_file_edit_history"  # type: ignore[assignment]
    __table_args__ = {"schema": "public"}

    history_id: uuid.UUID = Field(default_factory=uuid7, primary_key=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), index=True),
    )


class FileEditHistoryCreate(SQLModel):
    """Schema for creating a file edit history"""

    file_id: uuid.UUID
    target_type: str = Field(max_length=32)
    target_id: uuid.UUID
    marker_number: int
    editor_id: uuid.UUID
    text_before: str | None = None
    text_after: str
    comments: str | None = None


class FileEditHistoryCreateResponse(SQLModel):
    """Schema for creating a file edit history response"""

    history_id: uuid.UUID


class FileEditHistoryRead(FileEditHistoryBase):
    """Schema for reading a file edit history"""

    history_id: uuid.UUID
    created_at: datetime
