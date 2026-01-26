"""
File translation model

SQL Function                            Model Schema
--------------------------------------  ----------------------------------------------
au_create_file_translation              FileTranslationCreate, FileTranslationCreateResponse
au_update_file_translation              FileTranslationUpdate
au_delete_file_translation              FileTranslationDelete
au_get_file_translation_for_listing     FileTranslationReadForListing
au_get_file_translation_for_jsonb       FileTranslationReadForJsonb

See: scripts/schema-functions/schema-public.file.translation.sql
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Column, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel  # type: ignore[attr-defined]
from uuid_utils import uuid7


class FileTranslationBase(SQLModel):
    """Base file translation model"""

    file_id: uuid.UUID = Field(foreign_key="public.au_file_nodes.file_id", index=True)
    file_preset_id: uuid.UUID = Field(foreign_key="public.au_file_presets.file_preset_id")
    file_preset_json: dict[str, Any] = Field(sa_column=Column(JSONB))
    assignee_id: uuid.UUID
    translated_text: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))
    translated_text_modified: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))


class FileTranslation(FileTranslationBase, table=True):
    """File translation database model"""

    __tablename__ = "au_file_translation"  # type: ignore[assignment]
    __table_args__ = {"schema": "public"}

    translation_id: uuid.UUID = Field(default_factory=uuid7, primary_key=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), index=True),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True)),
    )
    deleted_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))


class FileTranslationCreate(SQLModel):
    """Schema for creating a file translation"""

    file_id: uuid.UUID
    file_preset_id: uuid.UUID
    file_preset_json: dict[str, Any]
    assignee_id: uuid.UUID
    translated_text: dict[str, Any] | None = None


class FileTranslationCreateResponse(SQLModel):
    """Schema for creating a file translation response"""

    translation_id: uuid.UUID


class FileTranslationUpdate(SQLModel):
    """Schema for updating a file translation"""

    translation_id: uuid.UUID
    translated_text: dict[str, Any] | None = None
    translated_text_modified: dict[str, Any] | None = None


class FileTranslationDelete(SQLModel):
    """Schema for deleting a file translation"""

    translation_id: uuid.UUID


class FileTranslationReadForListing(SQLModel):
    """Schema for reading a file translation (for listing, without jsonb)"""

    translation_id: uuid.UUID
    file_id: uuid.UUID
    file_preset_id: uuid.UUID
    file_preset_json: dict[str, Any]
    assignee_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class FileTranslationReadForJsonb(FileTranslationBase):
    """Schema for reading a file translation (with jsonb)"""

    translation_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
