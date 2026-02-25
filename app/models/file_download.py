"""
File download model

Pydantic request schema for file download (document generation).
Supports downloading text data from original, translation, or proofreading tables
as TXT, DOCX, PDF, or XLSX files.

Usage:
    POST /api/v1/file/download
    Body: FileDownloadRequest (file_id + exactly one of original_id, translation_id, proofreading_id)
"""

import uuid
from typing import Literal

from pydantic import model_validator
from sqlmodel import SQLModel  # type: ignore[attr-defined]


class FileDownloadRequest(SQLModel):
    """
    Schema for file download request.

    Requires file_id and exactly one of the three source IDs.
    The endpoint uses existing SQL functions to fetch text data,
    merges base + modified overlay (if version="latest"),
    and generates a file in the requested format.
    """

    # File ID (required -- used by existing SQL functions for lookup)
    file_id: uuid.UUID

    # Source ID (mutually exclusive -- exactly one required)
    original_id: uuid.UUID | None = None
    translation_id: uuid.UUID | None = None
    proofreading_id: uuid.UUID | None = None

    # Download options
    format: Literal["txt", "docx", "pdf", "xlsx"]
    include_numbers: bool = False
    column_title: str = "Download"

    # "original" = base text only, "latest" = merge base + modified overlay
    version: Literal["original", "latest"] = "latest"

    @model_validator(mode="after")
    def validate_exactly_one_id(self) -> "FileDownloadRequest":
        """Ensure exactly one of the three source IDs is provided"""
        provided = sum(
            1
            for field_value in [self.original_id, self.translation_id, self.proofreading_id]
            if field_value is not None
        )
        if provided != 1:
            raise ValueError("Exactly one of original_id, translation_id, or proofreading_id must be provided")
        return self
