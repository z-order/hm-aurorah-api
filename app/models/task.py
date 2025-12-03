"""
Task model
"""

from datetime import UTC, datetime
from enum import Enum

from sqlmodel import Field, SQLModel  # type: ignore[attr-defined]


class TaskStatus(str, Enum):
    """Task status enum"""

    TODO = "todo"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    """Task priority enum"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TaskBase(SQLModel):
    """Base task model"""

    title: str = Field(max_length=255, index=True)
    description: str | None = Field(default=None)
    status: TaskStatus = Field(default=TaskStatus.TODO)
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM)
    project_id: int = Field(foreign_key="sample_projects.id")
    assigned_to: int | None = Field(default=None, foreign_key="sample_users.id")


class Task(TaskBase, table=True):
    """Task database model"""

    __tablename__ = "sample_tasks"  # type: ignore[assignment]

    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    due_date: datetime | None = None


class TaskCreate(TaskBase):
    """Schema for creating a task"""

    due_date: datetime | None = None


class TaskUpdate(SQLModel):
    """Schema for updating a task"""

    title: str | None = Field(default=None, max_length=255)
    description: str | None = None
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    assigned_to: int | None = None
    due_date: datetime | None = None


class TaskRead(TaskBase):
    """Schema for reading a task"""

    id: int
    created_at: datetime
    updated_at: datetime
    due_date: datetime | None = None
