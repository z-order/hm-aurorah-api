"""
File original model

SQL Function                Model Schema
--------------------------  ----------------------------------------------
au_create_file_original     FileOriginalCreate, FileOriginalCreateResponse
au_update_file_original     FileOriginalUpdate
au_get_file_original        FileOriginalRead

See: scripts/schema-functions/schema-public.file.original.sql
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Column, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel  # type: ignore[attr-defined]
from uuid_utils import uuid7


class FileOriginalBase(SQLModel):
    """Base file original model"""

    file_id: uuid.UUID = Field(foreign_key="public.au_file_nodes.file_id", index=True)
    original_text: dict[str, Any] = Field(sa_column=Column(JSONB))
    original_text_modified: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))


class FileOriginal(FileOriginalBase, table=True):
    """File original database model"""

    __tablename__ = "au_file_original"  # type: ignore[assignment]
    __table_args__ = {"schema": "public"}

    original_id: uuid.UUID = Field(default_factory=uuid7, primary_key=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True)),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True)),
    )


class FileOriginalCreate(SQLModel):
    """Schema for creating a file original"""

    file_id: uuid.UUID
    original_text: dict[str, Any]


class FileOriginalCreateResponse(SQLModel):
    """Schema for creating a file original response"""

    original_id: uuid.UUID


class FileOriginalUpdate(SQLModel):
    """Schema for updating a file original"""

    original_id: uuid.UUID
    original_text: dict[str, Any] | None = None
    original_text_modified: dict[str, Any] | None = None


class FileOriginalRead(FileOriginalBase):
    """Schema for reading a file original"""

    original_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
