from app.utils.utils_text_metrics import TextMetrics, get_text_metrics

# ---- configurable head setting ----
MARKER_START = "┼"
MARKER_END = "┼"
DEFAULT_MIN_SENTENCE_LEN = 80
# -----------------------------------

# ---- Canonical pairs (left, right) ----
ENCLOSURE_PAIRS: list[tuple[str, str]] = [
    # ASCII
    ('"', '"'),
    ("'", "'"),
    ("(", ")"),
    ("[", "]"),
    ("{", "}"),
    ("<", ">"),
    # Guillemets
    ("«", "»"),
    ("‹", "›"),
    # “Smart” / typographic quotes
    ("“", "”"),
    ("‘", "’"),
    ("„", "”"),
    ("‚", "’"),
    # CJK quotes / brackets
    ("「", "」"),
    ("『", "』"),
    ("《", "》"),
    ("〈", "〉"),
    ("【", "】"),
    ("〔", "〕"),
    ("〖", "〗"),
    ("〘", "〙"),
    ("〚", "〛"),
    # Fullwidth forms
    ("（", "）"),
    ("［", "］"),
    ("｛", "｝"),
    ("＜", "＞"),
    ("【", "】"),
    # White / mathematical bracket family
    ("⟨", "⟩"),
    ("⟪", "⟫"),
    ("⟦", "⟧"),
    ("⟮", "⟯"),
    ("⟬", "⟭"),
    ("⦃", "⦄"),  # LEFT/RIGHT WHITE CURLY BRACKET
    ("⦅", "⦆"),  # LEFT/RIGHT WHITE PARENTHESIS
    # Small / presentation forms
    ("﹙", "﹚"),
    ("﹛", "﹜"),
    ("﹝", "﹞"),
    # Halfwidth corner quotes
    ("｢", "｣"),
]


# Rare self-closing symbols you may want to treat as their own pair
SELF_CLOSING: set[str] = {"⦿"}


def _build_enclosure_map() -> dict[str, str]:
    d: dict[str, str] = {}
    for left, right in ENCLOSURE_PAIRS:
        d[left] = right
        d[right] = left
    for ch in SELF_CLOSING:
        d[ch] = ch
    return d


# ---------------------------------------------------------------------
# Main function
# ---------------------------------------------------------------------


def add_sentence_markers(
    text: str,
    *,
    min_sentence_len: int = DEFAULT_MIN_SENTENCE_LEN,
    start_on_top_open: bool = True,
    end_on_top_close: bool = True,
    skip_empty_lines: bool = True,
    detect_line_wrapping: bool = False,
) -> str:
    """
    Insert sentence markers without altering original newlines and NEVER adding '\n'.

    Marker format:
      - Each marker is inserted as f"{MARKER_START}{N}{MARKER_END}" directly before the next segment.
        Examples: "┼1┼Hello", "【2】 Next".

    Recommended characters for MARKER_START/MARKER_END (choose one pair):
      - § (Section Sign) — e.g., §1 "Hello world."
      - ¤ (Currency Sign) — e.g., ¤1 "Hello world."
      - ‣ (Triangular Bullet) — e.g., ‣1 "Hello world."
      - ⁅ and ⁆ (Square Brackets with Quill) — e.g., ⁅1⁆ Hello world.
      - ⸢ and ⸣ (Corner Brackets) — e.g., ⸢1⸣ Hello world.
      - ⦿ (Black Circle with White Dot) — e.g., ⦿1 Hello world.
      - 【 and 】 (CJK brackets) — e.g., 【1】 Hello world. (recommended – clean and unique)
      - ┼ and ┼ (Cross) — e.g., ┼1┼ Hello world. (current default)

    Configuration:
      - Marker characters are controlled by module-level constants MARKER_START and MARKER_END.
      - min_sentence_len controls how long a segment may grow before a new marker is forced.
      - start_on_top_open/end_on_top_close govern whether top-level enclosures start/end segments.
      - skip_empty_lines keeps empty lines untouched.
      - detect_line_wrapping inspects text metrics to choose a marking strategy; never inserts '\n'.

    Rule:
      * Work per physical line (between original newlines).
      * If the whole line length <= min_sentence_len, insert ONLY ONE marker at that line start.
      * If the line length > min_sentence_len, insert additional markers ONLY at sentence starts,
        so each segment (from the last marker up to the next marker start) stays <= min_sentence_len.

    Sentence boundaries (inside each physical line only):
      - "...", "…", "‽", "?!", "!?", ".", "?", "!"
      - Top-level opening quotes/brackets
      - Top-level closing quotes/brackets (even without punctuation) if end_on_top_close=True
      (Balanced punctuation inside enclosures is ignored for boundary detection.)
    """

    # If the text is empty, return an empty string
    if not text:
        return ""

    # If detect_line_wrapping is True, get text metrics and check if line-wrapping
    if detect_line_wrapping:
        text_metrics = get_text_metrics(text)
        if text_metrics["is_line_wrapping"]:
            return _add_sentence_markers_for_line_wrapping(
                text,
                text_metrics,
                min_sentence_len=min_sentence_len,
                start_on_top_open=start_on_top_open,
                end_on_top_close=end_on_top_close,
                skip_empty_lines=skip_empty_lines,
            )

    # If detect_line_wrapping is False or the text is not line-wrapping, use the none line-wrapping method
    return _add_sentence_markers_for_none_line_wrapping(
        text,
        min_sentence_len=min_sentence_len,
        start_on_top_open=start_on_top_open,
        end_on_top_close=end_on_top_close,
        skip_empty_lines=skip_empty_lines,
    )


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------


def _add_sentence_markers_for_none_line_wrapping(
    text: str,
    *,
    min_sentence_len: int = DEFAULT_MIN_SENTENCE_LEN,
    start_on_top_open: bool = True,
    end_on_top_close: bool = True,
    skip_empty_lines: bool = True,
) -> str:
    # Split into (line, newline_cluster) pairs to preserve *exact* original separators
    lines = _split_lines_with_seps(text, double_line_feed=False)

    marker_no = 1
    out: list[str] = []

    # Loop through the lines and mark the sentences
    for line, sep in lines:
        # If the line is empty and skip_empty_lines is True, keep the line as is
        if skip_empty_lines and line.strip() == "":
            # Keep exactly as-is
            out.append(line)
            out.append(sep)
            continue

        # Mark the sentence in the line
        marked, marker_no = _mark_sentence_in_line(
            line,
            marker_no,
            min_sentence_len=min_sentence_len,
            start_on_top_open=start_on_top_open,
            end_on_top_close=end_on_top_close,
        )

        # Add the marked line to the output
        out.append(marked)
        out.append(sep)

    return "".join(out)


def _add_sentence_markers_for_line_wrapping(
    text: str,
    # text_metrics is for the future use (for updating line-wrapping algorithm)
    text_metrics: TextMetrics,
    *,
    min_sentence_len: int = DEFAULT_MIN_SENTENCE_LEN,
    start_on_top_open: bool = True,
    end_on_top_close: bool = True,
    skip_empty_lines: bool = True,
) -> str:
    """
    This function is the same code with _add_sentence_markers_for_none_line_wrapping except that it uses _split_lines_with_seps(text, double_line_feed=True)
    Maybe, the others will be updated in the future using text_metrics.
    """
    # Split into (line, newline_cluster) pairs to preserve *exact* original separators
    lines = _split_lines_with_seps(text, double_line_feed=True)

    marker_no = 1
    out: list[str] = []

    # Loop through the lines and mark the sentences
    for line, sep in lines:
        # If the line is empty and skip_empty_lines is True, keep the line as is
        if skip_empty_lines and line.strip() == "":
            # Keep exactly as-is
            out.append(line)
            out.append(sep)
            continue

        # Mark the sentence in the line
        marked, marker_no = _mark_sentence_in_line(
            line,
            marker_no,
            min_sentence_len=min_sentence_len,
            start_on_top_open=start_on_top_open,
            end_on_top_close=end_on_top_close,
        )

        # Add the marked line to the output
        out.append(marked)
        out.append(sep)

    return "".join(out)


def _split_lines_with_seps(text: str, double_line_feed: bool = False) -> list[tuple[str, str]]:
    """
    Return list of (line_without_linefeeds, separator) preserving *exact* separators.
    The last pair will have ``sep == ''`` when the input does **not** terminate with a
    newline *separator* according to the chosen rule.

    Parameters
    ----------
    text : str
        Input string.
    double_line_feed : bool, default False
        When ``False`` (default) **every** physical line‐feed (``\n``, ``\r`` or the
        Windows pair ``\r\n``) is treated as a separator.  When ``True`` we only break
        on *paragraph* separators – i.e. **two or more consecutive** line‐feeds
        (``\n\n``, ``\r\n\r\n`` …).  A single line‐feed will be kept **inside** the
        ``line`` part so that downstream code can preserve soft line-wraps.

    Examples
    --------
    >>> _split_lines_with_seps("Hello\nWorld\n\nHi")
    [('Hello', '\n'), ('World', '\n'), ('Hi', '')]

    >>> _split_lines_with_seps("Hello World!\nThis is a test.\r\nSecond line starts here.")
    [('Hello World!', '\n'), ('This is a test.', '\r\n'), ('Second line starts here.', '')]

    >>> _split_lines_with_seps("\n\n\n\n\nHello World!\nThis is a test.\r\nSecond line starts here.\n")
    [('Hello', '\n'), ('World', '\n'), ('Hi', '')]

    >>> _split_lines_with_seps("Hello World!\nThis is a test.\r\nSecond line starts here.\n\n\n \n\n")
    [('Hello World!', '\n'), ('This is a test.', '\r\n'), ('Second line starts here.', '\n\n\n'), (' ', '\n\n')]

    >>> _split_lines_with_seps("Hello\nWorld\n\nHi", double_line_feed=True)
    [('Hello\nWorld', '\n\n'), ('Hi', '')]

    >>> _split_lines_with_seps("Hello World!\nThis is a test.\r\n\r\nSecond line starts here.", double_line_feed=True)
    [('Hello World!\nThis is a test.', '\r\n\r\n'), ('Second line starts here.', '')]

    >>> _split_lines_with_seps("\n\n\n\n\nHello World!\nThis is a test.\n\nSecond line starts here.\n", double_line_feed=True)
    [('', '\n\n\n\n\n'), ('Hello World!\nThis is a test.', '\n\n'), ('Second line starts here.\n', '')]

    >>> _split_lines_with_seps("Hello World!\nThis is a test.\n\nSecond line starts here.\n\n\n \n\n", double_line_feed=True)
    [('Hello World!\nThis is a test.', '\n\n'), ('Second line starts here.', '\n\n\n'), (' ', '\n\n')]
    """

    # Fast-path for empty input --------------------------------------------------
    if not text:
        return [("", "")]

    n = len(text)
    res: list[tuple[str, str]] = []

    if not double_line_feed:
        # ------------------------------------------------------------------
        # Original behaviour – break on *every* line-feed cluster
        # ------------------------------------------------------------------
        i = 0
        while i < n:
            start = i
            # Collect non-line-feed characters
            while i < n and text[i] not in "\r\n":
                i += 1
            line = text[start:i]

            sep_start = i
            # Collect the full line-feed cluster (\n, \r or \r\n ...)
            while i < n and text[i] in "\r\n":
                i += 1
            sep = text[sep_start:i]
            res.append((line, sep))

        # If the input ended without a separator, ensure the invariant
        if text[-1] not in "\r\n":
            res.append(("", "")) if not res else None
        return res

    # ----------------------------------------------------------------------
    # double_line_feed = True – break only on 2+ consecutive line-feeds
    # ----------------------------------------------------------------------
    i = 0
    last = 0  # start index of current logical line
    single_lf_tokens = {"\n", "\r"}

    def consume_one_lf(idx: int) -> int:
        """Consume *one* logical line-feed (\n, \r or \r\n) and return new idx."""
        if text[idx] == "\r" and idx + 1 < n and text[idx + 1] == "\n":
            return idx + 2
        return idx + 1  # either \n or standalone \r

    while i < n:
        if text[i] not in single_lf_tokens:
            i += 1
            continue

        # Found at least one LF – determine how many *logical* LFs follow
        first_sep_start = i
        count = 0
        while i < n and text[i] in single_lf_tokens:
            i = consume_one_lf(i)
            count += 1

        # ``i`` now points **after** the run of LFs; ``sep`` is text[first_sep_start:i]
        sep = text[first_sep_start:i]

        if count >= 2:
            # Hard break – emit current line + separator
            line = text[last:first_sep_start]
            res.append((line, sep))
            last = i  # next logical line starts here
        # else: a single LF → treat as in-line char, do nothing

    # Tail after the final separator (or entire text if no separator seen)
    if last < n:
        res.append((text[last:], ""))
    elif not res:
        res.append(("", ""))

    return res


def _split_sentences_with_punctuations(text: str) -> list[tuple[str, str]]:  # pyright: ignore[reportUnusedFunction]
    """
    Return a list of ``(sentence, separator)`` pairs where ``sentence`` is the
    text between two sentence-ending punctuation clusters and ``separator`` is
    that punctuation cluster *including* any immediately following horizontal
    whitespace (spaces or tabs).  The final pair has ``separator == ''`` when
    the input does not terminate with a recognised sentence-ending sequence.

    This mirrors :pyfunc:`_split_lines_with_seps` but works at sentence level.
    We purposefully avoid a big pile of regular expressions and instead perform
    a single left-to-right scan so that the exact characters found in the
    source are preserved intact in the output.

    ex)
    print(_split_sentences_with_punctuations("Hello World!\nThis is a test.\r\nSecond line starts here."))
    # Output: [('Hello World', '!'), ('\nThis is a test', '.'), ('\r\nSecond line starts here', '.')]

    print(_split_sentences_with_punctuations("\n\n\n\n\nHello World!\nThis is a test.\r\nSecond line starts here.\n"))
    # Output: [('', '\n\n\n\n\n'), ('Hello World!', '\n'), ('This is a test.', '\r\n'), ('Second line starts here.', '\n')]

    print(_split_lines_with_seps("Hello World!\nThis is a test.\r\nSecond line starts here.\n\n\n \n\n"))
    # Output: [('Hello World!', '\n'), ('This is a test.', '\r\n'), ('Second line starts here.', '\n\n\n'), (' ', '\n\n')]
    """
    n = len(text)
    i = 0
    start = 0
    res: list[tuple[str, str]] = []

    while i < n:
        sep_start = -1  # will stay -1 if current char is not a boundary

        # ---- Detect sentence-ending punctuation clusters -----------------
        # Three-dot ellipsis "..."
        if text.startswith("...", i):
            sep_start = i
            i += 3
        # Unicode ellipsis "…"
        elif text[i] == "…":
            sep_start = i
            i += 1
        # Interrobang "‽"
        elif text[i] == "‽":
            sep_start = i
            i += 1
        # Paired marks "?!" or "!?"
        elif i + 1 < n and ((text[i] == "?" and text[i + 1] == "!") or (text[i] == "!" and text[i + 1] == "?")):
            sep_start = i
            i += 2
        # Single western or CJK punctuation marks
        elif text[i] in ".?!。？！":
            sep_start = i
            i += 1
        else:
            # Not a boundary – continue scanning
            i += 1
            continue

        # ---- Collect any trailing horizontal whitespace ------------------
        while i < n and text[i] in " \t":  # keep original spaces with separator
            i += 1
        sep_end = i

        # ---- Emit result pair -------------------------------------------
        sentence = text[start:sep_start]
        sep = text[sep_start:sep_end]
        res.append((sentence, sep))
        start = i  # next sentence starts after the separator

    # Remainder after the final separator (if any)
    if start < n:
        res.append((text[start:], ""))
    elif not res:
        # Handle empty input string the same way as _split_lines_with_seps
        res.append(("", ""))

    return res


def _mark_sentence_in_line(
    line: str,
    marker_no: int,
    *,
    min_sentence_len: int = DEFAULT_MIN_SENTENCE_LEN,
    start_on_top_open: bool,
    end_on_top_close: bool,
) -> tuple[str, int]:
    """
    This function inserts sentence markers at the beginning of each sentence in a line of text.
    And it has option to insert markers only when the sentence length is greater than min_sentence_len.
    If you want to insert markers for every sentence, set min_sentence_len to 0.

    It uses the function _sentence_starts_in_one_line to identify the start positions of sentences and then adds markers for each sentence.

    Returns: Tuple[str, int]
        - str: The line with sentence markers inserted at the appropriate positions.
        - int: The next marker number to be used.

    Steps:
        1. Identify Sentence Boundaries:
            It first calls _sentence_starts_in_one_line to get the start positions of each sentence in the line based on punctuation (like periods, question marks, exclamation marks, etc.).
        2. Insert Markers:
            For each identified sentence start, it adds a marker (┼N┼) at the beginning of the sentence. The markers are inserted in sequential order starting from 1.
        3. Return the Result:
            It returns the line with sentence markers inserted at the appropriate positions.

    Example 1:

        line = 'Hello? How are you! I am fine. Are you okay?!'
        print(_mark_every_sentence_in_line(line, 1, start_on_top_open=True, end_on_top_close=True))

        Expected Output:

        ('┼1┼Hello?┼2┼ How are you!┼3┼ I am fine.┼4┼ Are you okay?!', 5)

    Example 2:

        line = 'She said, "Hello there!" and walked away.'
        print(_mark_every_sentence_in_line(line, 1, start_on_top_open=True, end_on_top_close=True))

        Expected Output:

        ('┼1┼She said, ┼2┼"Hello there!"┼3┼ and walked away.', 4)
    """
    indices_of_starts = _sentence_starts_in_one_line(
        line, start_on_top_open=start_on_top_open, end_on_top_close=end_on_top_close
    )

    marked: list[str] = []
    chunks: list[str] = []

    def _marker_append():
        # Check if the first character is '\n' or '\r'
        if chunks[0][0] == "\n" or (chunks[0][0] == "\r" and chunks[0][1] == "\n"):
            linefeed = "\n" if chunks[0][0] == "\n" else "\r\n"
            marked.append(linefeed)
            chunks[0] = chunks[0][1:] if chunks[0][0] == "\n" else chunks[0][2:]
        # Add the marker and the chunks to the marked list
        marked.append(f"{MARKER_START}{marker_no}{MARKER_END}")
        marked.append("".join(chunks))

    # Loop through the indices of sentence starts
    for idx, s in enumerate(indices_of_starts):
        # end index of the current sentence
        e = indices_of_starts[idx + 1] if idx + 1 < len(indices_of_starts) else len(line)

        # Add the current sentence to the chunks
        chunks.append(line[s:e])

        # If min_sentence_len is 0, then set to 1 to avoid empty chunks
        if len("".join(chunks).strip()) < (1 if min_sentence_len == 0 else min_sentence_len):
            # If the current sentence length is less than min_sentence_len, add the sentence to the chunks
            continue
        # If the current sentence length is greater than min_sentence_len, add the marker and the chunks to the marked list and reset the chunks
        else:
            # Add the marker and the chunks to the marked list
            _marker_append()
            marker_no += 1
            chunks = []

    # If there are any chunks left, add the marker and the chunks to the marked list
    if len("".join(chunks).strip()) > 0:
        _marker_append()
        marker_no += 1

    return "".join(marked), marker_no


def _sentence_starts_in_one_line(
    line: str,
    *,
    start_on_top_open: bool,
    end_on_top_close: bool,
) -> list[int]:
    """
    Detect sentence starts inside a single physical line (no '\n' inside).

    Description:
        The function _sentence_starts_in_one_line detects sentence boundaries within a single physical line of text (i.e., without considering newlines).
        It identifies where each sentence starts, based on punctuation marks, enclosures (like quotes and parentheses), and specific sentence boundary markers such as ellipses,
        interrobangs, and punctuation marks (e.g., period, question mark, exclamation mark).

    How It Works:
        The function processes a line of text, keeping track of "open" and "close" enclosures (e.g., parentheses, quotes) and looking for sentence boundaries at specific positions.
        It detects sentence boundaries by checking for:
            - Ellipses (..., Unicode …).
            - Interrobangs (‽).
            - Punctuation pairs (?!, !?, ., ?, !).
            - Top-level enclosures, where an opening bracket or quote marks the start of a sentence.
        Top-level closing enclosures, which are treated as sentence boundaries if end_on_top_close=True.

    Example 1: Sentence Boundaries in a Line of Text

        line = 'Hello? How are you doing today!?'
        print(_sentence_starts_in_one_line(line, start_on_top_open=True, end_on_top_close=True))

        Expected Output:
        [0, 6]

        Explanation:
            - Sentence starts at position 0 ("Hello?"). line[0:] -> 'Hello? How are you doing today!?'
            - Sentence starts at position 6 (" How are you doing today!?"). line[6:] -> ' How are you doing today!?'
            - The function identifies two sentence boundaries, corresponding to the ? and !?.

    Example 2: Handling Enclosures

        line = 'She said, "Hello there!" and walked away.'
        print(_sentence_starts_in_one_line(line, start_on_top_open=True, end_on_top_close=True))

        Expected Output:
        [0, 10, 24]

        Explanation:
            - Sentence starts at position 0 ("She said"). line[0:] -> 'She said, "Hello there!" and walked away.'
            - The function identifies the sentence boundary inside the quotation marks at position 10 ("Hello there!"). line[10:] -> '"Hello there!" and walked away.'
            - The sentence finishes at position 24 with " and walked away." line[24:] -> ' and walked away.'

    Example 3: Handling Multiple Sentence-End Markers

        line = 'Is this it? Oh, I hope so... Yes!'
        print(_sentence_starts_in_one_line(line, start_on_top_open=True, end_on_top_close=True))

        Expected Output:
        [0, 11, 28]

        Explanation:
            - Sentence starts at position 0 ("Is this it?"). line[0:] -> 'Is this it? Oh, I hope so... Yes!'
            - Sentence starts at position 11 (" Oh, I hope so..."). line[11:] -> ' Oh, I hope so... Yes!'
            - Sentence starts at position 28 (" Yes!"). line[28:] -> ' Yes!'

    Example 4: Handling Unicode Ellipses and Interrobangs

        line = 'What is this… an interrobang‽ Really?'
        print(_sentence_starts_in_one_line(line, start_on_top_open=True, end_on_top_close=True))

        Expected Output:
        [0, 13, 29]

        Explanation:
            - Sentence starts at position 0 ("What is this…"). line[0:] -> 'What is this… an interrobang‽ Really?'
            - Sentence starts at position 13 (" an interrobang‽ Really?"). line[13:] -> ' an interrobang‽ Really?'
            - Sentence starts at position 29 (" Really?"). line[29:] -> ' Really?'
    """
    n = len(line)
    enclosures = _build_enclosure_map()
    opening = set(enclosures.keys())

    def match_boundary(i: int, stack: list[str]) -> int:
        if stack:
            return -1

        # Ellipsis "..."
        if line[i] == "." and i + 2 < n and line[i + 1] == "." and line[i + 2] == ".":
            return i + 3

        # Unicode ellipsis
        if line[i] == "…":
            return i + 1

        # Interrobang
        if line[i] == "‽":
            return i + 1

        # ?! or !?
        if i + 1 < n and ((line[i] == "?" and line[i + 1] == "!") or (line[i] == "!" and line[i + 1] == "?")):
            return i + 2

        # Single ., ?, !
        if line[i] in ".?!":
            return i + 1

        # CJK Single: 。？！
        if line[i] in "。？！":
            return i + 1

        return -1

    starts: list[int] = [0]
    stack: list[str] = []
    i = 0
    while i < n:
        c = line[i]

        if stack and c == stack[-1]:
            stack.pop()
            if end_on_top_close and not stack:
                next_pos = i + 1
                if next_pos < n and next_pos != starts[-1]:
                    starts.append(next_pos)
        elif c in opening:
            # Exception: ignore apostrophe if it's between alphanumeric characters (contractions like "don't", "it's", "didn’t ")
            if c in ("'", "’"):  # ASCII and typographic apostrophe
                is_contraction = False
                if 0 < i < n - 1:
                    prev_char = line[i - 1]
                    next_char = line[i + 1]
                    if prev_char.isalpha() and next_char.isalpha():
                        is_contraction = True
                if is_contraction:
                    i += 1
                    continue

            if start_on_top_open and not stack and i != starts[-1]:
                starts.append(i)
            stack.append(enclosures[c])

        end = match_boundary(i, stack)
        if end != -1:
            if end < n and end != starts[-1]:
                starts.append(end)
            i = end
            continue

        i += 1

    return starts
