import re
from typing import List


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


_ERROR_HEADER_RE = re.compile(
    r"""
    ^\s*
    (?:
        .*?                 # optional file path / prefix
        :\d+                # line number
        (?::\d+)*           # optional column / extra numeric fields
        :\s*
    )?
    (?:fatal\s+)?error      # error or fatal error
    (?:\[[^\]]+\])?         # optional Rust-style code, e.g. error[E0425]
    \s*:\s*
    (?P<message>.*?)
    \s*$
    """,
    re.IGNORECASE | re.VERBOSE,
)


def _looks_like_error_header(line: str) -> bool:
    return _ERROR_HEADER_RE.match(line) is not None


def _is_noise_line(line: str) -> bool:
    stripped = line.strip()

    if not stripped:
        return True

    # Caret markers:
    #   ^
    #   ^~~~
    #   ----
    if re.fullmatch(r"[\^~\-\s|]+", stripped):
        return True

    # Compiler source context gutters:
    #   56 |         bool found = false;
    #      |                      ^~~~~
    #   |
    if re.match(r"^\d+\s*\|", stripped):
        return True

    if re.match(r"^\|", stripped):
        return True

    # GCC/Clang include suggestion diff lines:
    #   +++ |+#include <stdbool.h>
    if stripped.startswith("+++") or stripped.startswith("---"):
        return True

    # Summary lines:
    #   3 errors
    #   error: aborting due to ...
    if re.fullmatch(r"\d+\s+errors?", stripped, re.IGNORECASE):
        return True

    return False


def _is_note_or_warning(line: str) -> bool:
    return re.search(r"\b(?:note|warning):", line, re.IGNORECASE) is not None


def _is_only_error_code(message: str) -> bool:
    """
    Examples:
      [GHC-58481]
      E0425
    """
    message = message.strip()
    return bool(
        re.fullmatch(r"\[[A-Za-z]+-\d+\]", message)
        or re.fullmatch(r"E\d{4}", message)
    )


def _clean_detail_line(line: str) -> str:
    line = line.strip()

    # Remove Haskell/Rust-style source gutter if present.
    line = re.sub(r"^\d+\s*\|\s?", "", line)
    line = re.sub(r"^\|\s?", "", line)

    return normalize_whitespace(line)


def extract_all_error_texts(compile_result: str) -> List[str]:
    if not compile_result:
        return []

    # If the string contains literal "\n" sequences instead of real newlines,
    # make it parseable.
    if "\\n" in compile_result and "\n" not in compile_result:
        compile_result = compile_result.replace("\\n", "\n")

    lower = compile_result.lower()
    if "compilation successful" in lower:
        return []

    # Remove wrapper prefix, but keep the actual diagnostics.
    compile_result = re.sub(
        r"^\s*compilation\s+error:\s*",
        "",
        compile_result,
        flags=re.IGNORECASE,
    )

    lines = compile_result.splitlines()
    errors: List[str] = []

    i = 0
    while i < len(lines):
        line = lines[i]
        match = _ERROR_HEADER_RE.match(line)

        if not match:
            i += 1
            continue

        message = normalize_whitespace(match.group("message"))

        details: List[str] = []

        j = i + 1
        while j < len(lines):
            next_line = lines[j]

            if _looks_like_error_header(next_line):
                break

            cleaned = _clean_detail_line(next_line)

            if not cleaned or _is_noise_line(next_line):
                j += 1
                continue

            # Ignore notes and warnings as separate diagnostic messages.
            # They are useful, but they are not primary errors.
            if _is_note_or_warning(next_line):
                j += 1
                continue

            # Useful detail lines from javac:
            #   symbol:   class Set
            #   location: class WordSpeller
            if re.match(r"^(symbol|location):", cleaned, re.IGNORECASE):
                details.append(cleaned)
                j += 1
                continue

            # Haskell/GHC often has:
            #   error: [GHC-58481]
            #       parse error on input ‘,’
            if not message or _is_only_error_code(message):
                details.append(cleaned)
                j += 1
                continue

            j += 1

        if details:
            if message:
                full_message = f"{message}; " + "; ".join(details)
            else:
                full_message = "; ".join(details)
        else:
            full_message = message

        full_message = normalize_whitespace(full_message)

        if full_message and re.search(r"[A-Za-z0-9]", full_message):
            errors.append(full_message)

        i = j

    # Fallback for odd formats.
    if not errors:
        text = normalize_whitespace(compile_result)
        if text and re.search(r"[A-Za-z0-9]", text):
            return [text]

    return errors