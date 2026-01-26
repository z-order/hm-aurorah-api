"""
System AI agent model

SQL Function                                    Model Schema
----------------------------------------------  ----------------------------------------------
au_system_upsert_ai_agent                       SystemAiAgentUpsert
au_system_create_ai_agent                       SystemAiAgentCreate
au_system_update_ai_agent                       SystemAiAgentUpdate
au_system_delete_ai_agent                       SystemAiAgentDelete
au_system_get_ai_agent                          SystemAiAgentRead

See: scripts/schema-functions/schema-public.system.ai-agent.sql
"""

from datetime import UTC, datetime

from sqlalchemy import Column, DateTime
from sqlmodel import Field, SQLModel  # type: ignore[attr-defined]


class SystemAiAgentBase(SQLModel):
    """Base system AI agent model"""

    ai_agent_id: str = Field(max_length=64, primary_key=True)
    ai_agent_title: str = Field(max_length=64, index=True)
    ai_agent_keyword: str = Field(max_length=64)
    ui_sort_order: str = Field(default="A0", max_length=64)
    description: str | None = Field(default=None, max_length=512)


class SystemAiAgent(SystemAiAgentBase, table=True):
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


class SystemAiAgentUpsert(SQLModel):
    """Schema for upserting a system AI agent"""

    ai_agent_id: str = Field(min_length=1, max_length=64)
    ai_agent_title: str = Field(min_length=1, max_length=64)
    ai_agent_keyword: str = Field(min_length=1, max_length=64)
    ui_sort_order: str = Field(default="A0", min_length=1, max_length=64)
    description: str | None = Field(default=None, max_length=512)


class SystemAiAgentCreate(SQLModel):
    """Schema for creating a system AI agent"""

    ai_agent_id: str = Field(min_length=1, max_length=64)
    ai_agent_title: str = Field(min_length=1, max_length=64)
    ai_agent_keyword: str = Field(min_length=1, max_length=64)
    ui_sort_order: str = Field(default="A0", min_length=1, max_length=64)
    description: str | None = Field(default=None, max_length=512)


class SystemAiAgentUpdate(SQLModel):
    """Schema for updating a system AI agent"""

    ai_agent_id: str = Field(min_length=1, max_length=64)
    ai_agent_title: str | None = Field(default=None, max_length=64)
    ai_agent_keyword: str | None = Field(default=None, max_length=64)
    ui_sort_order: str | None = Field(default=None, max_length=64)
    description: str | None = Field(default=None, max_length=512)


class SystemAiAgentDelete(SQLModel):
    """Schema for deleting a system AI agent"""

    ai_agent_id: str = Field(min_length=1, max_length=64)


class SystemAiAgentRead(SystemAiAgentBase):
    """Schema for reading a system AI agent"""

    created_at: datetime
    updated_at: datetime
