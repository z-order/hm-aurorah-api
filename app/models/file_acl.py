"""
File ACL model

SQL Function                Model Schema
--------------------------  ----------------------------------------------
au_create_file_acl          FileAclCreate
au_update_file_acl          FileAclUpdate
au_delete_file_acl          FileAclDelete
au_get_file_acl             FileAclRead

See: scripts/schema-functions/schema-public.file.acl.sql
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime
from sqlmodel import Field, SQLModel  # type: ignore[attr-defined]


class FileAclBase(SQLModel):
    """Base file ACL model"""

    file_id: uuid.UUID = Field(foreign_key="public.au_file_nodes.file_id", primary_key=True)
    principal_id: uuid.UUID = Field(primary_key=True)
    role: str = Field(default="viewer", max_length=32)


class FileAcl(FileAclBase, table=True):
    """File ACL database model"""

    __tablename__ = "au_file_acl"  # type: ignore[assignment]
    __table_args__ = {"schema": "public"}

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True)),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True)),
    )


class FileAclCreate(SQLModel):
    """Schema for creating a file ACL"""

    file_id: uuid.UUID
    principal_id: uuid.UUID
    role: str = Field(default="viewer", max_length=32)


class FileAclUpdate(SQLModel):
    """Schema for updating a file ACL"""

    file_id: uuid.UUID
    principal_id: uuid.UUID
    role: str = Field(max_length=32)


class FileAclDelete(SQLModel):
    """Schema for deleting a file ACL"""

    file_id: uuid.UUID
    principal_id: uuid.UUID


class FileAclRead(FileAclBase):
    """Schema for reading a file ACL"""

    created_at: datetime
    updated_at: datetime
