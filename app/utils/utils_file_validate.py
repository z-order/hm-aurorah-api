"""
File type validation utilities

Provides extension-based classification and magic bytes verification
for supported file formats.
"""

import io
import logging
import zipfile
from collections.abc import Callable
from enum import Enum

from app.core.logger import get_logger

logger = get_logger(__name__, logging.INFO)


class FileCategory(str, Enum):
    """Supported file type categories"""

    TEXT = "text"
    DOCX = "docx"
    PPTX = "pptx"
    XLSX = "xlsx"
    HWPX = "hwpx"
    PDF = "pdf"
    EPUB = "epub"
    RTF = "rtf"
    VIDEO = "video"


# Extension -> FileCategory mapping
_EXT_MAP: dict[str, FileCategory] = {
    ".txt": FileCategory.TEXT,
    ".srt": FileCategory.TEXT,
    ".vtt": FileCategory.TEXT,
    ".csv": FileCategory.TEXT,
    ".tsv": FileCategory.TEXT,
    ".rtf": FileCategory.RTF,
    ".docx": FileCategory.DOCX,
    ".pptx": FileCategory.PPTX,
    ".xlsx": FileCategory.XLSX,
    ".hwpx": FileCategory.HWPX,
    ".pdf": FileCategory.PDF,
    ".epub": FileCategory.EPUB,
    ".mp4": FileCategory.VIDEO,
    ".mkv": FileCategory.VIDEO,
    ".avi": FileCategory.VIDEO,
    ".mov": FileCategory.VIDEO,
    ".webm": FileCategory.VIDEO,
    ".flv": FileCategory.VIDEO,
    ".wmv": FileCategory.VIDEO,
}

SYNC_CATEGORIES: frozenset[FileCategory] = frozenset({FileCategory.TEXT})
ZIP_CATEGORIES: frozenset[FileCategory] = frozenset({
    FileCategory.DOCX,
    FileCategory.PPTX,
    FileCategory.XLSX,
    FileCategory.HWPX,
    FileCategory.EPUB,
})

ASYNC_CATEGORIES: frozenset[FileCategory] = frozenset({
    FileCategory.DOCX,
    FileCategory.PPTX,
    FileCategory.XLSX,
    FileCategory.HWPX,
    FileCategory.PDF,
    FileCategory.EPUB,
    FileCategory.RTF,
    FileCategory.VIDEO,
})


def validate_file_extension(file_ext: str) -> FileCategory:
    """
    Check if file extension is supported and return its category.

    Args:
        file_ext: File extension (e.g. ".pdf", ".docx"). Case-insensitive.

    Returns:
        FileCategory enum value

    Raises:
        ValueError: If extension is not supported
    """
    ext = file_ext.lower().strip()
    if not ext.startswith("."):
        ext = f".{ext}"

    category = _EXT_MAP.get(ext)
    if category is None:
        raise ValueError(f"Unsupported file extension: {file_ext}")

    return category


def validate_file_magic_bytes(file_bytes: bytes, file_ext: str) -> bool:
    """
    Verify that the file content matches the claimed extension using magic bytes.

    Args:
        file_bytes: First few KB of the file (at least 16 bytes; full file for ZIP-based)
        file_ext: Claimed file extension

    Returns:
        True if valid, False if mismatch
    """
    category = validate_file_extension(file_ext)

    if category == FileCategory.TEXT:
        return True

    if len(file_bytes) < 4:  # noqa: PLR2004
        return False

    validators: dict[FileCategory, Callable[[bytes, str], bool]] = {
        FileCategory.DOCX: _validate_zip_office("word/", require_content_types=True),
        FileCategory.PPTX: _validate_zip_office("ppt/", require_content_types=True),
        FileCategory.XLSX: _validate_zip_office("xl/", require_content_types=True),
        FileCategory.HWPX: _validate_hwpx,
        FileCategory.EPUB: _validate_epub,
        FileCategory.PDF: _validate_pdf,
        FileCategory.RTF: _validate_rtf,
        FileCategory.VIDEO: _validate_video,
    }

    validator = validators.get(category)
    if validator is None:
        return True

    try:
        return validator(file_bytes, file_ext)
    except Exception:
        logger.warning(f"Magic bytes validation error for {file_ext}", exc_info=True)
        return False


# ---------------------------------------------------------------------------
# ZIP-based Office formats (DOCX, PPTX, XLSX)
# ---------------------------------------------------------------------------

def _validate_zip_office(
    required_dir: str,
    require_content_types: bool = True,
) -> Callable[[bytes, str], bool]:
    """Factory: returns a validator for ZIP-based Office formats."""

    def _check(file_bytes: bytes, _ext: str) -> bool:
        if file_bytes[:4] != b"PK\x03\x04":
            return False

        try:
            with zipfile.ZipFile(io.BytesIO(file_bytes)) as zf:
                names = zf.namelist()
                if require_content_types and "[Content_Types].xml" not in names:
                    return False
                if not any(n.startswith("_rels/") for n in names):
                    return False
                if not any(n.startswith(required_dir) for n in names):
                    return False
            return True
        except zipfile.BadZipFile:
            return False

    return _check


# ---------------------------------------------------------------------------
# HWPX
# ---------------------------------------------------------------------------

def _validate_hwpx(file_bytes: bytes, _ext: str) -> bool:
    if file_bytes[:4] != b"PK\x03\x04":
        return False

    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as zf:
            names = zf.namelist()
            has_contents = any(n.startswith("Contents/") for n in names)
            has_meta_inf = "META-INF/manifest.xml" in names
            return has_contents and has_meta_inf
    except zipfile.BadZipFile:
        return False


# ---------------------------------------------------------------------------
# EPUB
# ---------------------------------------------------------------------------

def _validate_epub(file_bytes: bytes, _ext: str) -> bool:
    if file_bytes[:4] != b"PK\x03\x04":
        return False

    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as zf:
            names = zf.namelist()
            if not names or names[0] != "mimetype":
                return False
            mimetype_content = zf.read("mimetype").decode("ascii", errors="ignore").strip()
            return mimetype_content == "application/epub+zip"
    except (zipfile.BadZipFile, KeyError):
        return False


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------

def _validate_pdf(file_bytes: bytes, _ext: str) -> bool:
    return file_bytes[:5] == b"%PDF-"


# ---------------------------------------------------------------------------
# RTF
# ---------------------------------------------------------------------------

def _validate_rtf(file_bytes: bytes, _ext: str) -> bool:
    return len(file_bytes) >= 5 and file_bytes[:5] == b"{\\rtf"  # noqa: PLR2004


# ---------------------------------------------------------------------------
# Video formats
# ---------------------------------------------------------------------------

_ASF_GUID = bytes.fromhex("3026B2758E66CF11A6D900AA0062CE6C")


def _validate_video(file_bytes: bytes, file_ext: str) -> bool:
    ext = file_ext.lower().strip()
    if not ext.startswith("."):
        ext = f".{ext}"

    if ext in (".mp4", ".mov"):
        return len(file_bytes) >= 8 and file_bytes[4:8] == b"ftyp"

    if ext in (".mkv", ".webm"):
        return file_bytes[:4] == b"\x1a\x45\xdf\xa3"

    if ext == ".avi":
        return len(file_bytes) >= 12 and file_bytes[:4] == b"RIFF" and file_bytes[8:12] == b"AVI "

    if ext == ".flv":
        return file_bytes[:3] == b"FLV"

    if ext == ".wmv":
        return len(file_bytes) >= 16 and file_bytes[:16] == _ASF_GUID

    return True
