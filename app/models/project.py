"""
Project model
"""

from datetime import UTC, datetime
from enum import Enum

from sqlalchemy import Column, String
from sqlmodel import Field, SQLModel  # type: ignore[attr-defined]


class ProjectStatus(str, Enum):
    """Project status enum"""

    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class ProjectBase(SQLModel):
    """Base project model"""

    name: str = Field(max_length=255, index=True)
    description: str | None = Field(default=None)
    status: ProjectStatus = Field(
        default=ProjectStatus.DRAFT,
        sa_column=Column(String(32)),
    )
    user_id: int = Field(foreign_key="sample_users.id")


class Project(ProjectBase, table=True):
    """Project database model"""

    __tablename__ = "sample_projects"  # type: ignore[assignment]

    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ProjectCreate(ProjectBase):
    """Schema for creating a project"""

    pass


class ProjectUpdate(SQLModel):
    """Schema for updating a project"""

    name: str | None = Field(default=None, max_length=255)
    description: str | None = None
    status: ProjectStatus | None = None


class ProjectRead(ProjectBase):
    """Schema for reading a project"""

    id: int
    created_at: datetime
    updated_at: datetime
