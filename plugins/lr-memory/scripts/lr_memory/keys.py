"""Key-shaped strings never go into the index or out of a search: each one is replaced by a marker."""
from __future__ import annotations

import re

PATTERNS = (
    r"sk-ant-[A-Za-z0-9_\-]{20,}",  # Anthropic
    r"(?<![\w-])sk-(?:proj-)?[A-Za-z0-9_\-]{32,}",  # OpenAI
    r"\bgh[pousr]_[A-Za-z0-9]{36,}|\bgithub_pat_[A-Za-z0-9_]{60,}",  # GitHub
    r"\bAKIA[0-9A-Z]{16}\b",  # AWS
    r"\bAIza[0-9A-Za-z_\-]{35}\b",  # Google
    r"\bxox[abprs]-[A-Za-z0-9\-]{10,}",  # Slack
    r"\bhf_[A-Za-z0-9]{30,}",  # Hugging Face
    r"KAGGLE_KEY\s*[=:]\s*[\"']?[0-9a-f]{32}",  # Kaggle
)
COMPILED = tuple(re.compile(p) for p in PATTERNS)
# a cheap first look: most texts carry none of these, and the full patterns run only on the ones that do
PREFILTER = re.compile(r"sk-ant-|sk-proj-|sk-[A-Za-z0-9_-]{32}|AKIA[0-9A-Z]|gh[pousr]_|github_pat_|AIza|xox[abprs]-|"
                       r"hf_[A-Za-z0-9]|KAGGLE_KEY|PRIVATE KEY-----")
PRIVATE_BLOCK = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?(?:-----END [A-Z ]*PRIVATE KEY-----|\Z)", re.S)
MARK = "[secret]"


def mask(text: str) -> str:
    if not PREFILTER.search(text):
        return text
    text = PRIVATE_BLOCK.sub(MARK, text)
    for rx in COMPILED:
        text = rx.sub(MARK, text)
    return text
