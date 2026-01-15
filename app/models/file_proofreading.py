"""
File proofreading model

SQL Function                              Model Schema
----------------------------------------  ----------------------------------------------
au_create_file_proofreading               FileProofreadingCreate, FileProofreadingCreateResponse
au_update_file_proofreading               FileProofreadingUpdate
au_delete_file_proofreading               FileProofreadingDelete
au_get_file_proofreading_for_listing      FileProofreadingReadForListing
au_get_file_proofreading_for_jsonb        FileProofreadingReadForJsonb

See: scripts/schema-functions/schema-public.file.proofreading.sql
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Column, DateTime
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Field, SQLModel  # type: ignore[attr-defined]
from uuid_utils import uuid7


class FileProofreadingBase(SQLModel):
    """Base file proofreading model"""

    file_id: uuid.UUID = Field(foreign_key="public.au_file_nodes.file_id", index=True)
    assignee_id: uuid.UUID | None = Field(default=None)
    participant_ids: list[uuid.UUID] | None = Field(default=None, sa_column=Column(ARRAY(PG_UUID)))  # type: ignore[var-annotated]
    proofreaded_text: dict[str, Any] = Field(sa_column=Column(JSONB))


class FileProofreading(FileProofreadingBase, table=True):
    """File proofreading database model"""

    __tablename__ = "au_file_proofreading"  # type: ignore[assignment]
    __table_args__ = {"schema": "public"}

    proofreading_id: uuid.UUID = Field(default_factory=uuid7, primary_key=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), index=True),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True)),
    )
    deleted_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))


class FileProofreadingCreate(SQLModel):
    """Schema for creating a file proofreading"""

    file_id: uuid.UUID
    assignee_id: uuid.UUID | None = None
    participant_ids: list[uuid.UUID] | None = None
    proofreaded_text: dict[str, Any]


class FileProofreadingCreateResponse(SQLModel):
    """Schema for creating a file proofreading response"""

    proofreading_id: uuid.UUID


class FileProofreadingUpdate(SQLModel):
    """Schema for updating a file proofreading"""

    proofreading_id: uuid.UUID
    assignee_id: uuid.UUID | None = None
    participant_ids: list[uuid.UUID] | None = None
    proofreaded_text: dict[str, Any] | None = None


class FileProofreadingDelete(SQLModel):
    """Schema for deleting a file proofreading"""

    proofreading_id: uuid.UUID


class FileProofreadingReadForListing(SQLModel):
    """Schema for reading a file proofreading (for listing, without jsonb)"""

    proofreading_id: uuid.UUID
    file_id: uuid.UUID
    assignee_id: uuid.UUID | None = None
    participant_ids: list[uuid.UUID] | None = None
    created_at: datetime
    updated_at: datetime


class FileProofreadingReadForJsonb(FileProofreadingBase):
    """Schema for reading a file proofreading (with jsonb)"""

    proofreading_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
