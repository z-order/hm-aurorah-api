"""
System LLM model

SQL Function                                    Model Schema
----------------------------------------------  ----------------------------------------------
au_system_upsert_llm_model                      SystemLLMModelUpsert
au_system_create_llm_model                      SystemLLMModelCreate
au_system_update_llm_model                      SystemLLMModelUpdate
au_system_delete_llm_model                      SystemLLMModelDelete
au_system_get_llm_model                         SystemLLMModelRead

See: scripts/schema-functions/schema-public.system.llm-model.sql
"""

from datetime import UTC, datetime

from sqlalchemy import Column, DateTime
from sqlmodel import Field, SQLModel  # type: ignore[attr-defined]


class SystemLLMModelBase(SQLModel):
    """Base system LLM model"""

    llm_model_id: str = Field(max_length=64, primary_key=True)
    llm_model_title: str = Field(max_length=64, index=True)
    llm_model_keyword: str = Field(max_length=64)
    ui_sort_order: str = Field(default="A0", max_length=64)
    description: str | None = Field(default=None, max_length=512)
    provider: str = Field(max_length=64)


class SystemLLMModel(SystemLLMModelBase, table=True):
    """System LLM model database model"""

    __tablename__ = "au_system_llm_models"  # type: ignore[assignment]
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


class SystemLLMModelUpsert(SQLModel):
    """Schema for upserting a system LLM model"""

    llm_model_id: str = Field(min_length=1, max_length=64)
    llm_model_title: str = Field(min_length=1, max_length=64)
    llm_model_keyword: str = Field(min_length=1, max_length=64)
    ui_sort_order: str = Field(default="A0", min_length=1, max_length=64)
    description: str | None = Field(default=None, max_length=512)
    provider: str = Field(min_length=1, max_length=64)


class SystemLLMModelCreate(SQLModel):
    """Schema for creating a system LLM model"""

    llm_model_id: str = Field(min_length=1, max_length=64)
    llm_model_title: str = Field(min_length=1, max_length=64)
    llm_model_keyword: str = Field(min_length=1, max_length=64)
    ui_sort_order: str = Field(default="A0", min_length=1, max_length=64)
    description: str | None = Field(default=None, max_length=512)
    provider: str = Field(min_length=1, max_length=64)


class SystemLLMModelUpdate(SQLModel):
    """Schema for updating a system LLM model"""

    llm_model_id: str = Field(min_length=1, max_length=64)
    llm_model_title: str | None = Field(default=None, max_length=64)
    llm_model_keyword: str | None = Field(default=None, max_length=64)
    ui_sort_order: str | None = Field(default=None, max_length=64)
    description: str | None = Field(default=None, max_length=512)
    provider: str | None = Field(default=None, max_length=64)


class SystemLLMModelDelete(SQLModel):
    """Schema for deleting a system LLM model"""

    llm_model_id: str = Field(min_length=1, max_length=64)


class SystemLLMModelRead(SystemLLMModelBase):
    """Schema for reading a system LLM model"""

    created_at: datetime
    updated_at: datetime
