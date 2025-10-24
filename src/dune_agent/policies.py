from typing import Tuple

DENYLIST = ["system prompt", "reveal instructions", "password", "secret"]


def sanitize_input(text: str) -> str:
    cleaned = text.replace("\x00", "").strip()
    return cleaned


def policy_check(output: str) -> Tuple[bool, str]:
    lower = output.lower()
    for token in DENYLIST:
        if token in lower:
            return False, "Output contains disallowed content"
    return True, ""
