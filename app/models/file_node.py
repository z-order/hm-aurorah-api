"""
File node model

SQL Function                Model Schema
--------------------------  ----------------------------------------------
au_create_file              FileNodeCreate, FileNodeCreateResponse
au_update_file              FileNodeUpdate
au_delete_file              FileNodeDelete
au_duplicate_file           FileNodeDuplicate, FileNodeDuplicateResponse
au_move_file                FileNodeMove
au_get_files                FileNodeRead

See: scripts/schema-functions/schema-public.file.file.sql
"""

import uuid
from datetime import UTC, datetime
from enum import Enum

from sqlalchemy import Column, DateTime
from sqlmodel import Field, SQLModel  # type: ignore[attr-defined]
from uuid_utils import uuid7


class FileType(str, Enum):
    """File type"""

    FOLDER = "folder"
    FILE = "file"


class FileNodeBase(SQLModel):
    """Base file node model"""

    owner_id: str = Field(index=True)  # Foreign key to auth.users.id is managed outside SQLModel.
    parent_file_id: uuid.UUID | None = Field(default=None, index=True)
    file_type: FileType = Field(default=FileType.FOLDER)
    file_name: str = Field(max_length=512)
    file_url: str | None = Field(default=None, max_length=1024)
    file_ext: str = Field(default="", max_length=32)
    file_size: int = Field(default=0)
    mime_type: str | None = Field(default=None, max_length=32)
    description: str | None = Field(default=None, max_length=512)


class FileNode(FileNodeBase, table=True):
    """File node database model"""

    __tablename__ = "au_file_nodes"  # type: ignore[assignment]
    __table_args__ = {"schema": "public"}

    file_id: uuid.UUID = Field(default_factory=uuid7, primary_key=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), index=True),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), index=True),
    )
    deleted_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))


class FileNodeCreate(SQLModel):
    """Schema for creating a file node"""

    owner_id: str = Field(min_length=1, max_length=255)
    parent_file_id: uuid.UUID | None = Field(default=None)
    file_type: FileType = Field(default=FileType.FOLDER)
    file_name: str = Field(min_length=1, max_length=512)
    file_url: str | None = Field(default=None, max_length=1024)
    file_ext: str = Field(default="", max_length=32)
    file_size: int = Field(default=0, ge=0)
    mime_type: str | None = Field(default=None, max_length=32)
    description: str | None = Field(default=None, max_length=512)


class FileNodeCreateResponse(SQLModel):
    """Schema for creating a file node response"""

    file_id: uuid.UUID


class FileNodeUpdate(SQLModel):
    """Schema for updating a file node"""

    file_name: str | None = Field(default=None, max_length=512)
    description: str | None = Field(default=None, max_length=512)


class FileNodeRead(FileNodeBase):
    """Schema for reading a file node"""

    file_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None


class FileNodeDelete(SQLModel):
    """Schema for deleting a file node"""

    file_id: uuid.UUID


class FileNodeMove(SQLModel):
    """Schema for moving a file node"""

    file_id: uuid.UUID
    new_parent_file_id: uuid.UUID | None = Field(default=None)


class FileNodeDuplicate(SQLModel):
    """Schema for duplicating a file node"""

    file_id: uuid.UUID


class FileNodeDuplicateResponse(SQLModel):
    """Schema for duplicating a file node response"""

    file_id: uuid.UUID
