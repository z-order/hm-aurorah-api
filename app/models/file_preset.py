"""
File preset model

SQL Function                Model Schema
--------------------------  ----------------------------------------------
au_create_file_preset       FilePresetCreate, FilePresetCreateResponse
au_update_file_preset       FilePresetUpdate
au_delete_file_preset       FilePresetDelete
au_get_file_preset          FilePresetRead

See: scripts/schema-functions/schema-public.file.preset.sql
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime
from sqlmodel import Field, SQLModel  # type: ignore[attr-defined]
from uuid_utils import uuid7


class FilePresetBase(SQLModel):
    """Base file preset model"""

    principal_id: uuid.UUID = Field(index=True)
    description: str = Field(max_length=128)
    llm_model_id: str = Field(max_length=64)
    llm_model_temperature: int
    ai_agent_id: str = Field(default="agent_translation_a1", max_length=64)
    translation_memory: str | None = Field(default=None, max_length=256)
    translation_role: str | None = Field(default=None)
    translation_rule: str | None = Field(default=None)
    target_language: str = Field(max_length=128)
    target_country: str = Field(max_length=128)
    target_city: str | None = Field(default=None, max_length=128)
    task_type: str = Field(default="localization", max_length=32)
    audience: str = Field(default="general")
    purpose: str


class FilePreset(FilePresetBase, table=True):
    """File preset database model"""

    __tablename__ = "au_file_presets"  # type: ignore[assignment]
    __table_args__ = {"schema": "public"}

    file_preset_id: uuid.UUID = Field(default_factory=uuid7, primary_key=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True)),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), index=True),
    )
    deleted_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))


class FilePresetCreate(SQLModel):
    """Schema for creating a file preset"""

    principal_id: uuid.UUID
    description: str = Field(min_length=1, max_length=128)
    llm_model_id: str = Field(min_length=1, max_length=64)
    llm_model_temperature: int
    ai_agent_id: str | None = Field(default="agent_translation_a1", max_length=64)
    translation_memory: str | None = Field(default=None, max_length=256)
    translation_role: str | None = None
    translation_rule: str | None = None
    target_language: str = Field(min_length=1, max_length=128)
    target_country: str = Field(min_length=1, max_length=128)
    target_city: str | None = Field(default=None, max_length=128)
    task_type: str = Field(default="localization", max_length=32)
    audience: str = Field(default="general")
    purpose: str = Field(min_length=1)


class FilePresetCreateResponse(SQLModel):
    """Schema for creating a file preset response"""

    file_preset_id: uuid.UUID


class FilePresetUpdate(SQLModel):
    """Schema for updating a file preset"""

    file_preset_id: uuid.UUID
    description: str | None = Field(default=None, max_length=128)
    llm_model_id: str | None = Field(default=None, max_length=64)
    llm_model_temperature: int | None = None
    ai_agent_id: str | None = Field(default=None, max_length=64)
    translation_memory: str | None = Field(default=None, max_length=256)
    translation_role: str | None = None
    translation_rule: str | None = None
    target_language: str | None = Field(default=None, max_length=128)
    target_country: str | None = Field(default=None, max_length=128)
    target_city: str | None = Field(default=None, max_length=128)
    task_type: str | None = Field(default=None, max_length=32)
    audience: str | None = None
    purpose: str | None = None


class FilePresetDelete(SQLModel):
    """Schema for deleting a file preset"""

    file_preset_id: uuid.UUID


class FilePresetRead(FilePresetBase):
    """Schema for reading a file preset"""

    file_preset_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
