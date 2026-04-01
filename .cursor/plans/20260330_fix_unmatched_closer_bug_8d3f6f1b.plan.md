---
name: Fix unmatched closer bug
overview: "Fix _sentence_starts_in_one_line: (1) skip unmatched closing brackets that corrupt the stack, (2) add fallback so that even inside a legitimately opened enclosure, if text exceeds min_sentence_len the punctuation detection resumes."
todos:
  - id: build-closers-set
    content: Add `_CLOSERS` set built from ENCLOSURE_PAIRS at module level
    status: completed
  - id: skip-unmatched-closers
    content: In `_sentence_starts_in_one_line`, skip closing chars that have no matching opener on the stack
    status: completed
  - id: enclosure-fallback
    content: In `match_boundary`, allow punctuation detection when inside enclosure but distance from opener exceeds min_sentence_len
    status: completed
  - id: verify-examples
    content: Verify the 4 existing docstring examples still produce correct output
    status: completed
isProject: false
---

# Fix Enclosure Stack Issues in Sentence Boundary Detection

Single file change: [app/utils/utils_sentence_numbering.py](app/utils/utils_sentence_numbering.py)

## Root cause

`_sentence_starts_in_one_line` (line 526) uses an enclosure `stack` to suppress punctuation detection inside brackets/quotes. Two problems:

1. **Unmatched closers corrupt the stack**: `_build_enclosure_map` maps both directions (`(` -> `)` and `)` -> `(`), so `)` in `1)` `2)` `3)` is treated as an opener, pushes `(` onto the stack, and all subsequent `.` `?` `!` are suppressed.
2. **No fallback for long enclosures**: Even when enclosures are legitimately opened, if the content inside is very long (e.g. OCR text with mismatched brackets spanning hundreds of chars), all sentence boundaries inside are suppressed forever.

## Fix 1: Skip unmatched closers

Add a `_CLOSERS` set at module level (line ~60):

```python
_CLOSERS: set[str] = {right for _, right in ENCLOSURE_PAIRS}
```

In the `elif c in opening` branch (line 647), before pushing onto the stack, check: if `c` is a closer and the stack has no matching opener, skip it:

```python
# Skip unmatched closers -- e.g. "1)" "2)" "3)" numbering patterns
# where ")" appears without a preceding "(" on the stack.
# Without this guard the orphan closer pushes onto the stack and
# corrupts enclosure tracking, suppressing all downstream "." "?" "!"
# sentence boundary detection.
if c in _CLOSERS and (not stack or stack[-1] != c):
    i += 1
    continue
```

This preserves all existing enclosure tracking -- only orphan closers are ignored.

## Fix 2: Enclosure distance fallback in match_boundary

Currently `match_boundary` (line 605) unconditionally returns `-1` when the stack is non-empty:

```python
def match_boundary(i: int, stack: list[str]) -> int:
    if stack:
        return -1
```

Change the stack to track opener positions: `list[tuple[str, int]]`. Then allow punctuation detection when the distance from the most recent opener exceeds `min_sentence_len`:

```python
# Allow sentence boundary detection even inside an enclosure when the
# distance from the most recent opener exceeds min_sentence_len.
# This is a safety net: short enclosures like "(Web)" or "[그림 1]"
# still suppress punctuation as intended, but if an opener was never
# closed and we've scanned past min_sentence_len characters, we
# resume splitting to avoid producing one giant segment.
def match_boundary(i: int, stack: list[tuple[str, int]], min_len: int) -> int:
    if stack and (i - stack[-1][1]) < min_len:
        return -1
```

This means:

- Short enclosures like `(Web)`, `[그림 1]` -- distance < 80, punctuation suppressed (as-is)
- Long broken enclosures where opener is 80+ chars ago -- punctuation detection resumes

## Changes to stack usage

The stack changes from `list[str]` to `list[tuple[str, int]]`:

- `stack.append(enclosures[c])` becomes `stack.append((enclosures[c], i))`
- `stack[-1]` comparisons use `stack[-1][0]` for the character
- `stack.pop()` stays the same
