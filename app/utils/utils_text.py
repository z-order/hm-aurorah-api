import json
import logging
import re

from app.utils.utils_sentence_numbering import MARKER_END, MARKER_START, add_sentence_markers

logger = logging.getLogger(__name__)


def _try_parse_json_segments(raw_text: str) -> dict[str, list[dict[str, str | int]]] | None:
    """
    Try to parse raw_text as JSON with a "segments" array.

    Guards against the nested JSON bug: if the input is already a JSON object
    like {"segments": [{"sid": 1, "text": "..."}, ...]}, parse it directly
    instead of wrapping it as a single segment via add_sentence_markers().

    Args:
        raw_text: Raw text that might be a JSON string

    Returns:
        Parsed segments dict if valid JSON with segments, else None
    """
    stripped = raw_text.strip()
    if not stripped.startswith("{"):
        return None

    try:
        parsed = json.loads(stripped)
    except (json.JSONDecodeError, ValueError):
        return None

    if not isinstance(parsed, dict):
        return None

    segments = parsed.get("segments")
    if not isinstance(segments, list) or len(segments) == 0:
        return None

    # Validate segment structure: each must have "sid" and "text"
    valid: list[dict[str, str | int]] = []
    for seg in segments:
        if isinstance(seg, dict) and "sid" in seg and "text" in seg:
            valid.append({"sid": seg["sid"], "text": str(seg["text"])})

    if valid:
        logger.info(f"[analyze_raw_text_to_json] Detected JSON segments input ({len(valid)} segments), parsed directly")
        return {"segments": valid}

    return None


def analyze_raw_text_to_json(raw_text: str) -> dict[str, list[dict[str, str | int]]]:
    """
    Analyze raw text file and convert to JSON format with sentence markers.

    Handles 3 input formats:
    1. JSON with segments  - {"segments": [{"sid": 1, "text": "..."}, ...]}
    2. Marker-delimited    - ┼1┼First sentence.┼2┼Second sentence. ...
    3. Plain text          - unmarked text (auto-marked via add_sentence_markers)

    Args:
        raw_text: The raw text content of the file (can be JSON, pre-marked, or unmarked)

    Returns:
        Dictionary with 'segments' key containing list of sentence objects.
        Example: {"segments": [{"sid": 1, "text": "First sentence."}, {"sid": 2, "text": "Second sentence."}, ...]}
    """
    # -------------------------------------------------------------------------
    # Guard: Try JSON parse first to prevent nested JSON bug.
    # If the input is already a JSON segments object, return it directly
    # instead of wrapping it as a single marker segment.
    # -------------------------------------------------------------------------
    json_result = _try_parse_json_segments(raw_text)
    if json_result is not None:
        return json_result

    # -------------------------------------------------------------------------
    # Normal path: ┼N┼ marker parsing or auto-marking plain text
    # -------------------------------------------------------------------------
    marker_pattern = re.escape(MARKER_START) + r"(\d+)" + re.escape(MARKER_END)

    # Check if text is already marked
    if re.search(marker_pattern, raw_text):
        original_text_marked = raw_text
    else:
        # Mark the original text with sentence markers
        original_text_marked = add_sentence_markers(
            raw_text,
            start_on_top_open=True,
            end_on_top_close=True,
            skip_empty_lines=True,
            detect_line_wrapping=True,
        )

    # Parse the marked text into a list of dictionaries
    segments: list[dict[str, str | int]] = []

    # Find all markers and their positions
    matches = list(re.finditer(marker_pattern, original_text_marked))

    # Calculate text length once to avoid repeated calls
    text_length = len(original_text_marked)
    matches_count = len(matches)

    for i, match in enumerate(matches):
        # Extract sentence ID from the marker (e.g., "┼1┼" -> 1)
        sid = int(match.group(1))
        # Text starts right after the marker ends
        start_pos = match.end()
        # Text ends at the next marker's start, or end of string if last segment
        end_pos = matches[i + 1].start() if i + 1 < matches_count else text_length
        # Extract the text content between markers
        text_value = original_text_marked[start_pos:end_pos]
        # Append segment with sentence ID and text content
        segments.append({"sid": sid, "text": text_value})

    return {"segments": segments}
