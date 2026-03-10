from urllib.parse import quote, urlparse, urlunparse

import httpx
from charset_normalizer import from_bytes
from fastapi import HTTPException, status

from app.core.logger import get_logger

logger = get_logger(__name__)


def _encode_url_path(file_url: str) -> str:
    """Encode URL path to handle special characters like spaces and Korean."""
    parsed = urlparse(file_url)
    encoded_path = quote(parsed.path, safe="/")
    return urlunparse(parsed._replace(path=encoded_path))


def decode_bytes(raw: bytes) -> str:
    """Decode bytes to str with encoding auto-detection.

    Strips BOM if present, then uses charset_normalizer to detect encoding.
    Falls back to utf-8 with replacement on failure.
    """
    # Strip UTF-8 BOM
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw[3:].decode("utf-8")

    # Strip UTF-16 BOM
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16")

    result = from_bytes(raw)
    best = result.best()
    if best is not None:
        encoding = str(best.encoding)
        logger.debug(f"Detected encoding: {encoding} (confidence: {best.encoding})")
        return raw.decode(encoding)

    return raw.decode("utf-8", errors="replace")


async def read_raw_text_file_from_url(file_url: str) -> str:
    """
    Read raw text file content from URL.

    Args:
        file_url: The URL to read the file from

    Returns:
        The raw text content of the file

    Raises:
        HTTPException: If the file cannot be read
    """
    try:
        encoded_url = _encode_url_path(file_url)
        async with httpx.AsyncClient() as client:
            response = await client.get(encoded_url)
            response.raise_for_status()
            return decode_bytes(response.content)
    except httpx.HTTPStatusError as e:
        logger.error(f"Failed to read file from CDN server, URL: {file_url}, status: {e.response.status_code}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to read file from CDN server: {e.response.status_code}",
        )
    except Exception as e:
        logger.error(f"Failed to read file from CDN server, URL: {file_url}, error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to read file from CDN server",
        )


async def read_binary_file_from_url(file_url: str, timeout: float = 120.0) -> bytes:
    """
    Read binary file content from URL.

    Args:
        file_url: The URL to read the file from
        timeout: Request timeout in seconds (default 120s for large files)

    Returns:
        The raw binary content of the file

    Raises:
        HTTPException: If the file cannot be read
    """
    try:
        encoded_url = _encode_url_path(file_url)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(encoded_url)
            response.raise_for_status()
            return response.content
    except httpx.HTTPStatusError as e:
        logger.error(f"Failed to read file from CDN server, URL: {file_url}, status: {e.response.status_code}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to read file from CDN server: {e.response.status_code}",
        )
    except Exception as e:
        logger.error(f"Failed to read file from CDN server, URL: {file_url}, error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to read file from CDN server",
        )


async def read_file_header_from_url(file_url: str, size: int = 8192) -> bytes:
    """
    Read the first N bytes of a file from URL (for magic bytes validation).

    Args:
        file_url: The URL to read from
        size: Number of bytes to read (default 8KB)

    Returns:
        The first N bytes of the file

    Raises:
        HTTPException: If the file cannot be read
    """
    try:
        encoded_url = _encode_url_path(file_url)
        async with httpx.AsyncClient() as client:
            response = await client.get(encoded_url, headers={"Range": f"bytes=0-{size - 1}"})
            if response.status_code not in (200, 206):
                response.raise_for_status()
            return response.content[:size]
    except httpx.HTTPStatusError as e:
        logger.error(f"Failed to read file header from CDN server, URL: {file_url}, status: {e.response.status_code}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to read file header from CDN server: {e.response.status_code}",
        )
    except Exception as e:
        logger.error(f"Failed to read file header from CDN server, URL: {file_url}, error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to read file header from CDN server",
        )
