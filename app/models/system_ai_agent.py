"""
System AI agent model

SQL Function                                    Model Schema
----------------------------------------------  ----------------------------------------------
au_system_upsert_ai_agent                       SystemAIAgentUpsert
au_system_create_ai_agent                       SystemAIAgentCreate
au_system_update_ai_agent                       SystemAIAgentUpdate
au_system_delete_ai_agent                       SystemAIAgentDelete
au_system_get_ai_agent                          SystemAIAgentRead

See: scripts/schema-functions/schema-public.system.ai-agent.sql
"""

from datetime import UTC, datetime

from sqlalchemy import Column, DateTime
from sqlmodel import Field, SQLModel  # type: ignore[attr-defined]


class SystemAIAgentBase(SQLModel):
    """Base system AI agent model"""

    ai_agent_id: str = Field(max_length=64, primary_key=True)
    ai_agent_title: str = Field(max_length=64, index=True)
    ai_agent_keyword: str = Field(max_length=64)
    ui_sort_order: str = Field(default="A0", max_length=64)
    description: str | None = Field(default=None, max_length=512)


class SystemAIAgent(SystemAIAgentBase, table=True):
    """System AI agent database model"""

    __tablename__ = "au_system_ai_agents"  # type: ignore[assignment]
    __table_args__ = {"schema": "public"}

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True)),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True)),
    )
    deleted_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True), index=True))


class SystemAIAgentUpsert(SQLModel):
    """Schema for upserting a system AI agent"""

    ai_agent_id: str = Field(min_length=1, max_length=64)
    ai_agent_title: str = Field(min_length=1, max_length=64)
    ai_agent_keyword: str = Field(min_length=1, max_length=64)
    ui_sort_order: str = Field(default="A0", min_length=1, max_length=64)
    description: str | None = Field(default=None, max_length=512)


class SystemAIAgentCreate(SQLModel):
    """Schema for creating a system AI agent"""

    ai_agent_id: str = Field(min_length=1, max_length=64)
    ai_agent_title: str = Field(min_length=1, max_length=64)
    ai_agent_keyword: str = Field(min_length=1, max_length=64)
    ui_sort_order: str = Field(default="A0", min_length=1, max_length=64)
    description: str | None = Field(default=None, max_length=512)


class SystemAIAgentUpdate(SQLModel):
    """Schema for updating a system AI agent"""

    ai_agent_id: str = Field(min_length=1, max_length=64)
    ai_agent_title: str | None = Field(default=None, max_length=64)
    ai_agent_keyword: str | None = Field(default=None, max_length=64)
    ui_sort_order: str | None = Field(default=None, max_length=64)
    description: str | None = Field(default=None, max_length=512)


class SystemAIAgentDelete(SQLModel):
    """Schema for deleting a system AI agent"""

    ai_agent_id: str = Field(min_length=1, max_length=64)


class SystemAIAgentRead(SystemAIAgentBase):
    """Schema for reading a system AI agent"""

    created_at: datetime
    updated_at: datetime
