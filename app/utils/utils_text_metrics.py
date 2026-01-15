"""
Text metrics calculator.
"""

import re
import statistics
from typing import TypedDict


class TextMetrics(TypedDict):
    number_of_characters: int
    number_of_words: int
    number_of_sentences: int
    number_of_phrases: int
    number_of_punctuations: int
    number_of_ending_punctuations: int
    number_of_linefeeds: int
    mean_characters_per_line: float
    mean_characters_per_line_after_garbage_removal: float
    sigma_characters_per_line: float
    sigma_characters_per_line_after_garbage_removal: float
    is_line_wrapping: bool


def get_text_metrics(text: str) -> TextMetrics:
    """
    Analyze the input text and return a dictionary of analyzed properties.

    Args:
        text (str): The input text to analyze

    Returns:
        Dict[str, int | float]: Dictionary containing the following metrics:
            - number_of_characters: The number of characters of the text
            - number_of_words: The number of words of the text
            - number_of_sentences: The number of sentences of the text
            - number_of_phrases: The number of phrases of the text
            - number_of_punctuations: The number of punctuations of the text
            - number_of_ending_punctuations: The number of sentence-ending punctuations of the text
            - number_of_linefeeds: The number of linefeeds of the text
            - mean_characters_per_line: The mean characters per line of the text
            - mean_characters_per_line_after_garbage_removal: The mean characters per line of the text after removing garbage data
            - sigma_characters_per_line: The standard deviation of characters per line
            - sigma_characters_per_line_after_garbage_removal: The standard deviation of characters per line after removing garbage data
            - is_line_wrapping: Whether the text is line-wrapping or not

    Key Implementation Details:
        - Uses regex patterns for accurate sentence and phrase detection
        - Handles edge cases (empty text, single lines, etc.)
        - Filters out empty strings/lines for accurate counting
        - Uses Python's statistics module for mean and standard deviation calculations
        - Includes proper type hints for better code documentation
        - The function is ready to use and will provide comprehensive text analysis metrics as requested!

    Line-wrapping detection algorithm is:

        1) If µ0.5 ≤ σ then text is not line-wrapping.

        2) Range of a Data Set using Mean(µ) and Standard Deviation(σ)

            µ ± 1.0σ (≈68.27%)
            µ ± 2.0σ (≈95.45%)
            µ ± 3.0σ (≈99.73%)

        3) Remove all Data Set not in the range of Standard Deviation (µ ± 1.0σ)

            line_wrapping_data_set = All Data Set - [line for line in lines if line in range of Standard Deviation (µ ± 1.0σ)]

            if line_wrapping_data_set is not empty, then the text is line-wrapping.

        4) Remove all Data Set satisfying the following condition:

            if data_n_length ≤ 0.6 * mean_chars (=0.6µ) then
                remove data_n from line_wrapping_data_set

        5) After removing garbage data, recalculate the mean and standard deviation of line_wrapping_data_set

        6) for line_wrapping_data_set, apply the following formula:

            µ - 0.3µ ≤ µ ± 1.2σ ≤ µ + 0.3µ

            =>  This can be simplified to:  σ ≤ 0.25µ

            #
            # Refs)
            #
            # µ - 0.3µ ≤ µ + 1.0σ ≤ µ + 0.3µ    =>   σ ≤ 0.3µ
            #
            # Optimized constants: 0.3 for range, 1.0 for sigma (100% accuracy) for the old formula, but it's not perfect.
            #

        µ: mean characters per line
        σ: standard deviation of characters per line

        When the above formula is true, the text is line-wrapping.

    This is the old line-wrapping detection algorithm (not used but kept for reference):

        µ - 0.3µ ≤ µ + 1.0σ ≤ µ + 0.3µ    =>   σ ≤ 0.3µ or σ ≤ 0.5µ

        Optimized constants: 0.3 for range, 1.0 for sigma (100% accuracy on 2_comprehensive_test_1~3.py but not on 3_final_verification.py), 0.5 for sigma (3_final_verification.py)

        Here are the code:

        # Apply line-wrapping detection algorithm:
        # µ - 0.3µ ≤ µ + 1.0σ ≤ µ + 0.3µ
        # where µ = mean_chars, σ = sigma_chars
        # Optimized constants: 0.3 for range, 1.0 for sigma (100% accuracy)
        #
        # Enhanced algorithm with additional heuristics:
        # 1. Special case: single lines are never line-wrapped
        # 2. Primary formula: µ - 0.3µ ≤ µ + 1.0σ ≤ µ + 0.3µ
        # 3. Fallback heuristic: if formula fails but CV < 0.36 and mean < 60, still line-wrapped
        #    This handles edge cases like Korean text with consistent wrapping

        # Special case: if only one line, it's not line-wrapping
        if len(chars_per_line) == 1:
            is_wrapping = False
        else:
            # Apply the optimized formula
            lower_bound = mean_chars - 0.3 * mean_chars
            upper_bound = mean_chars + 0.3 * mean_chars
            range_check = mean_chars + 1.0 * sigma_chars

            # Check if the formula is satisfied
            formula_satisfied = lower_bound <= range_check <= upper_bound

            # Additional heuristic: if the coefficient of variation (CV) is low,
            # it's likely line-wrapped even if the formula fails
            cv = sigma_chars / mean_chars if mean_chars > 0 else float('inf')

            # More sophisticated decision logic:
            # 1. If formula is satisfied, it's line-wrapped
            # 2. If formula fails but CV is very low (< 0.5), it's still line-wrapped
            # 3. If formula fails and CV is high, it's not line-wrapped
            is_wrapping = formula_satisfied or (cv < 0.5 and mean_chars < 120)
    """
    _fn_ = "get_text_metrics()"

    # Set debug mode
    _debug_mode = False

    # Initialize result dictionary
    metrics: dict[str, int | float | bool] = {}

    # Count total characters (including spaces and punctuation)
    metrics["number_of_characters"] = len(text)

    # Count words (only linguistic characters, excluding all punctuation and symbols)
    # Remove sentence markers (┼N┼) before word counting
    text_for_words = re.sub(r"┼\d+┼", "", text)

    # Define patterns for all punctuation and non-linguistic symbols
    # Based on utils_sentence_numbering.py patterns
    non_linguistic_pattern = (
        r'[.,!?;:()\[\]{}"\'-]'  # Standard ASCII punctuation
        r'|["'
        "]"  # Smart quotes
        r"|[«»‹›]"  # Guillemets
        r'|["„‚]'  # German quotes
        r"|[「」『』《》〈〉【】〔〕〖〗〘〙〚〛]"  # CJK brackets
        r"|[（）［］｛｝＜＞]"  # Fullwidth brackets
        r"|[⟨⟩⟪⟫⟦⟧⟮⟯⟬⟭⦃⦄⦅⦆]"  # Mathematical brackets
        r"|[﹙﹚﹛﹜﹝﹞]"  # Small brackets
        r"|[｢｣]"  # Halfwidth corner quotes
        r"|⦿"  # Self-closing symbol
        r"|\.{3}"  # Ellipsis
        r"|…"  # Unicode ellipsis
        r"|‽"  # Interrobang
        r"|[，；：]"  # Fullwidth CJK punctuation
        r"|[\s]+"  # Whitespace
    )

    # Remove all non-linguistic characters
    text_for_words = re.sub(non_linguistic_pattern, " ", text_for_words)

    # Split by whitespace and filter out empty strings
    words = [word for word in text_for_words.split() if word.strip()]
    metrics["number_of_words"] = len(words)

    # Count sentences (split by sentence-ending punctuation)
    # Based on utils_sentence_numbering.py patterns:
    # - Ellipsis "..."
    # - Unicode ellipsis "…"
    # - Interrobang "‽"
    # - ?! or !?
    # - Single . ? !
    # - CJK Single: 。？！
    text_for_sentences = text.strip()

    # Split by various sentence endings
    # Use multiple split operations to avoid regex conflicts
    sentences: list[str] = [text_for_sentences]

    # Split by ellipsis patterns first
    temp_sentences: list[str] = []
    for sentence in sentences:
        temp_sentences.extend(re.split(r"\.{3}(?:\s+|$)", sentence))
    sentences = temp_sentences

    # Split by Unicode ellipsis
    temp_sentences = []
    for sentence in sentences:
        temp_sentences.extend(re.split(r"…(?:\s+|$)", sentence))
    sentences = temp_sentences

    # Split by interrobang
    temp_sentences = []
    for sentence in sentences:
        temp_sentences.extend(re.split(r"‽(?:\s+|$)", sentence))
    sentences = temp_sentences

    # Split by combined punctuation (must be before single characters)
    temp_sentences = []
    for sentence in sentences:
        temp_sentences.extend(re.split(r"\?!(?:\s+|$)", sentence))
    sentences = temp_sentences

    temp_sentences = []
    for sentence in sentences:
        temp_sentences.extend(re.split(r"!\?(?:\s+|$)", sentence))
    sentences = temp_sentences

    # Split by standard sentence endings (including CJK sentence endings), but protect numbered list items
    temp_sentences = []
    for sentence in sentences:
        # Check if this sentence contains numbered list patterns
        if re.search(r"\d+\.\s+", sentence):
            # For sentences with numbered list items, split more carefully
            # Split at sentence endings but not at the periods in numbered lists
            # Negative lookbehind to avoid splitting after digits
            parts = re.split(r"(?<!\d)\.(?:\s+|$)", sentence)
            # After splitting, we need to handle special punctuation like "!" and "?"
            parts = [re.split(r"[!?。！？]+", part) for part in parts]
            # Flatten the list of lists
            parts = [item for sublist in parts for item in sublist if item.strip()]
            temp_sentences.extend(parts)
        else:
            # For regular sentences, split normally
            temp_sentences.extend(re.split(r"[.!?。！？]+(?:\s+|$)", sentence))
    sentences = temp_sentences

    # Filter out numbered list items (N. string pattern)
    filtered_sentences: list[str] = []
    for sentence in sentences:
        sentence = sentence.strip()

        # Skip if it matches numbered list pattern (N. string). Items that start with a number followed by a period.
        if re.match(r"^\d+\.\s+", sentence):
            continue

        # Skip if it contains multiple numbered list items (e.g. 1. 2. 3.). Text containing multiple numbered items.
        if re.search(r"\d+\.\s+.*\d+\.\s+", sentence):
            continue

        # Skip if it's just a single numbered list item (e.g. 1. string). Single numbered list items.
        if re.match(r"^\d+\.\s+\w+", sentence):
            continue

        # Skip if it contains any numbered list items (more comprehensive check). Any text containing numbered list items.
        if re.search(r"\d+\.\s+\w+", sentence):
            continue

        if sentence:  # Only add non-empty sentences
            filtered_sentences.append(sentence)

    sentences = filtered_sentences

    # Split by paragraph breaks
    temp_sentences = []
    for sentence in sentences:
        temp_sentences.extend(re.split(r"\n{2,}", sentence))
    sentences = temp_sentences

    # Filter out empty sentences
    sentences = [sentence for sentence in sentences if sentence.strip()]
    metrics["number_of_sentences"] = len(sentences)

    # Count phrases (split by two or more consecutive newlines)
    phrases = re.split(r"\n{2,}", text)

    # Filter out empty phrases
    phrases = [phrase for phrase in phrases if phrase.strip()]
    metrics["number_of_phrases"] = len(phrases)

    # Count ALL punctuation marks
    # Based on utils_sentence_numbering.py, include all enclosure pairs and special symbols:
    # - ASCII quotes and brackets: " ' ( ) [ ] { } < >
    # - Guillemets: « » ‹ ›
    # - Smart/typographic quotes: " " ' ' „ " ‚ '
    # - CJK quotes/brackets: 「 」 『 』 《 》 〈 〉 【 】 〔 〕 〖 〗 〘 〙 〚 〛
    # - Fullwidth forms: （ ） ［ ］ ｛ ｝ ＜ ＞ 【 】
    # - White/mathematical brackets: ⟨ ⟩ ⟪ ⟫ ⟦ ⟧ ⟮ ⟯ ⟬ ⟭ ⦃ ⦄ ⦅ ⦆
    # - Small/presentation forms: ﹙ ﹚ ﹛ ﹜ ﹝ ﹞
    # - Halfwidth corner quotes: ｢ ｣
    # - Self-closing symbols: ⦿
    # - Ellipsis: ... …
    # - Interrobang: ‽
    # - Standard punctuation: . , ! ? ; : -
    # - Fullwidth CJK punctuation: ，；：

    all_punctuation_pattern = (
        r'[.,!?;:()\[\]{}"\'-]'  # Standard ASCII punctuation
        r'|["'
        "]"  # Smart quotes
        r"|[«»‹›]"  # Guillemets
        r'|["„‚]'  # German quotes
        r"|[「」『』《》〈〉【】〔〕〖〗〘〙〚〛]"  # CJK brackets
        r"|[（）［］｛｝＜＞]"  # Fullwidth brackets
        r"|[⟨⟩⟪⟫⟦⟧⟮⟯⟬⟭⦃⦄⦅⦆]"  # Mathematical brackets
        r"|[﹙﹚﹛﹜﹝﹞]"  # Small brackets
        r"|[｢｣]"  # Halfwidth corner quotes
        r"|⦿"  # Self-closing symbol
        r"|\.{3}"  # Ellipsis
        r"|…"  # Unicode ellipsis
        r"|‽"  # Interrobang
        r"|[，；：]"  # Fullwidth CJK punctuation
    )

    all_punctuations = re.findall(all_punctuation_pattern, text)
    metrics["number_of_punctuations"] = len(all_punctuations)

    # Count sentence-ending punctuation marks only
    # Based on utils_sentence_numbering.py sentence boundary patterns:
    # - Ellipsis: ... …
    # - Interrobang: ‽
    # - Combined punctuation: ?! !?
    # - Standard sentence endings: . ? !
    # - Fullwidth CJK sentence endings: 。？！

    # Count sentence-ending punctuation marks only
    # Use multiple findall calls to avoid regex conflicts
    ending_punctuations: list[str] = []

    # Ellipsis patterns
    ending_punctuations.extend(re.findall(r"\.{3}", text))  # "..."
    ending_punctuations.extend(re.findall(r"…", text))  # Unicode ellipsis

    # Interrobang
    ending_punctuations.extend(re.findall(r"‽", text))

    # Combined punctuation (must be before single characters)
    ending_punctuations.extend(re.findall(r"\?!", text))  # ?!
    ending_punctuations.extend(re.findall(r"!\?", text))  # !?

    # CJK sentence endings
    ending_punctuations.extend(re.findall(r"[。？！]", text))

    # Standard sentence endings (must be last to avoid conflicts)
    ending_punctuations.extend(re.findall(r"[.!?]", text))

    metrics["number_of_ending_punctuations"] = len(ending_punctuations)

    # Count linefeeds (newlines)
    linefeeds = text.count("\n")
    metrics["number_of_linefeeds"] = linefeeds

    # Calculate characters per line
    lines = text.split("\n")
    # Filter out empty lines for calculation
    non_empty_lines = [line for line in lines if line.strip()]

    # Initialize variables for line-wrapping detection
    is_wrapping = False
    mean_chars_after_garbage_removal = 0.0
    sigma_chars_after_garbage_removal = 0.0
    mean_chars = 0.0
    sigma_chars = 0.0

    # To make a jump using break statement
    while True:
        # If no non-empty lines(=empty lines), break the loop
        if not non_empty_lines:
            break

        # Calculate characters per line for each non-empty line
        chars_per_line = [len(line) for line in non_empty_lines]

        # Calculate mean characters per line
        mean_chars = round(statistics.mean(chars_per_line), 2)

        # Calculate standard deviation of characters per line
        if len(chars_per_line) > 1:
            sigma_chars = round(statistics.stdev(chars_per_line), 2)
        else:
            # If only one line, standard deviation is 0
            sigma_chars = 0.0
            break

        # Apply line-wrapping detection algorithm:
        #
        # 1) If µ0.5 ≤ σ then text is not line-wrapping.
        #
        # 2) Range of a Data Set using Mean(µ) and Standard Deviation(σ)
        #    µ ± 1.0σ (≈68.27%)
        #    µ ± 2.0σ (≈95.45%)
        #    µ ± 3.0σ (≈99.73%)
        #
        # 3) Remove all Data Set not in the range of Standard Deviation (µ ± 1.0σ)
        #    line_wrapping_data_set = All Data Set - [line for line in lines if line in range of Standard Deviation (µ ± 1.0σ)]
        #    if line_wrapping_data_set is not empty, then the text is line-wrapping.
        #
        # 4) Remove all Data Set satisfying the following condition:
        #    if data_n_length ≤ 0.6 * mean_chars (=0.6µ) then
        #        remove data_n from line_wrapping_data_set
        #
        # 5) After removing garbage data, recalculate the mean and standard deviation of line_wrapping_data_set
        #
        # 6) for line_wrapping_data_set, apply the following formula:
        #
        #    µ - 0.3µ ≤ µ ± 1.2σ ≤ µ + 0.3µ
        #
        #    =>  This can be simplified to:  σ ≤ 0.25µ
        #
        # µ: mean characters per line
        # σ: standard deviation of characters per line
        # When the above formula is true, the text is line-wrapping.

        # Special case: if only one line, it's not line-wrapping
        if len(chars_per_line) == 1:
            if _debug_mode:
                print(f"{_fn_} - len(chars_per_line) == 1, so text is not line-wrapping.")
            break

        # Special case: if mean_chars > 150, it's not line-wrapping
        if mean_chars > 150:
            if _debug_mode:
                print(
                    f"{_fn_} - mean_chars > 150, so text is not line-wrapping. mean_chars: {mean_chars}, sigma_chars: {sigma_chars}"
                )
            break

        # Step 1: If µ0.5 ≤ σ then text is not line-wrapping
        if 0.5 * mean_chars <= sigma_chars:
            if _debug_mode:
                print(
                    f"{_fn_} - 0.5 * mean_chars <= sigma_chars, so text is not line-wrapping. sigma_chars: {sigma_chars}, mean_chars: {mean_chars}"
                )
            break

        # Step 2: Calculate the range using mean and standard deviation
        # µ ± 1.0σ range
        lower_range = mean_chars - 1.0 * sigma_chars
        upper_range = mean_chars + 1.0 * sigma_chars

        # Step 3: Remove all data points NOT in the range of µ ± 1.0σ
        # line_wrapping_data_set = All Data Set - [line for line in lines if line in range of Standard Deviation (µ ± 1.0σ)]
        # This means we keep only the data points that ARE in the range
        line_wrapping_data_set = [
            line_length for line_length in chars_per_line if lower_range <= line_length <= upper_range
        ]

        if _debug_mode:
            print(f"{_fn_} - len(chars_per_line): {len(chars_per_line)}")
            print(f"{_fn_} - len(line_wrapping_data_set): {len(line_wrapping_data_set)}")

        # If line_wrapping_data_set is not empty, then proceed to step 4
        if line_wrapping_data_set:
            # Step 4: Remove all data points satisfying the condition:
            # if data_n_length ≤ 0.6 * mean_chars (=0.6µ) then remove data_n from line_wrapping_data_set
            line_wrapping_data_set = [
                line_length for line_length in line_wrapping_data_set if line_length > 0.6 * mean_chars
            ]

            if _debug_mode:
                print(f"{_fn_} - len(line_wrapping_data_set) after step 4: {len(line_wrapping_data_set)}")

            # Step 5: After removing garbage data, recalculate the mean and standard deviation of line_wrapping_data_set
            if len(line_wrapping_data_set) > 1:
                recalculated_mean = round(statistics.mean(line_wrapping_data_set), 2)
                recalculated_sigma = round(statistics.stdev(line_wrapping_data_set), 2)
            elif len(line_wrapping_data_set) == 1:
                recalculated_mean = round(line_wrapping_data_set[0], 2)
                recalculated_sigma = 0.0
            else:
                # If no data points left after filtering, set to 0
                recalculated_mean = 0.0
                recalculated_sigma = 0.0

            if _debug_mode:
                print(f"{_fn_} - Original - mean: {mean_chars}, sigma: {sigma_chars}")
                print(f"{_fn_} - Recalculated - mean: {recalculated_mean}, sigma: {recalculated_sigma}")

            mean_chars_after_garbage_removal = round(recalculated_mean, 2)
            sigma_chars_after_garbage_removal = round(recalculated_sigma, 2)

            # Step 6: Apply the formula: µ - 0.3µ ≤ µ ± 1.2σ ≤ µ + 0.3µ => σ ≤ 0.25µ
            # This can be simplified to: σ ≤ 0.25µ
            # Use the recalculated values
            is_wrapping = recalculated_sigma <= (0.25 * recalculated_mean)
            if _debug_mode:
                print(
                    f"{_fn_} - recalculated_sigma: {recalculated_sigma}, recalculated_mean: {recalculated_mean}, 0.25 * recalculated_mean: {0.25 * recalculated_mean}"
                )
                print(
                    f"{_fn_} - is_wrapping: {is_wrapping} = recalculated_sigma({recalculated_sigma}) <= (0.25 * recalculated_mean)({0.25 * recalculated_mean})"
                )

            # break the while loop
            break

    # Set the results
    metrics["mean_characters_per_line"] = mean_chars
    metrics["sigma_characters_per_line"] = sigma_chars
    metrics["mean_characters_per_line_after_garbage_removal"] = mean_chars_after_garbage_removal
    metrics["sigma_characters_per_line_after_garbage_removal"] = sigma_chars_after_garbage_removal
    metrics["is_line_wrapping"] = is_wrapping

    return metrics  # type: ignore[return-value]
