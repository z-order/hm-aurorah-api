from urllib.parse import quote, urlparse, urlunparse

import httpx
from fastapi import HTTPException, status

from app.core.logger import get_logger

logger = get_logger(__name__)


def _encode_url_path(file_url: str) -> str:
    """Encode URL path to handle special characters like spaces and Korean."""
    parsed = urlparse(file_url)
    encoded_path = quote(parsed.path, safe="/")
    return urlunparse(parsed._replace(path=encoded_path))


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
            return response.text
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
