"""
User model
"""

from datetime import UTC, datetime

from sqlmodel import Field, SQLModel  # type: ignore[attr-defined]


class UserBase(SQLModel):
    """Base user model"""

    email: str = Field(unique=True, index=True, max_length=255)
    username: str = Field(unique=True, index=True, max_length=100)
    full_name: str | None = Field(default=None, max_length=255)
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)


class User(UserBase, table=True):
    """User database model"""

    __tablename__ = "sample_users"  # type: ignore[assignment]

    id: int | None = Field(default=None, primary_key=True)
    hashed_password: str = Field(max_length=255)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class UserCreate(UserBase):
    """Schema for creating a user"""

    password: str = Field(min_length=8, max_length=100)


class UserUpdate(SQLModel):
    """Schema for updating a user"""

    email: str | None = Field(default=None, max_length=255)
    username: str | None = Field(default=None, max_length=100)
    full_name: str | None = Field(default=None, max_length=255)
    password: str | None = Field(default=None, min_length=8, max_length=100)
    is_active: bool | None = None
    is_superuser: bool | None = None


class UserRead(UserBase):
    """Schema for reading a user"""

    id: int
    created_at: datetime
    updated_at: datetime
