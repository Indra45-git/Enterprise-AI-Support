"""
Guardrails module.

Production note: this exposes the same check_input()/check_output() interface that a
real NVIDIA NeMo Guardrails integration would use (see /backend/app/guardrails/nemo_config/
for the config.yml + rails.co stubs to swap in). Running actual NeMo Guardrails requires a
guardrails LLM call per turn and heavier dependencies; for this environment we implement the
same *contract* with deterministic heuristic rules so the security control points in the
architecture (input guard -> agent -> output guard) are real and testable end-to-end.
"""
import re
from dataclasses import dataclass

INJECTION_PATTERNS = [
    r"ignore (all )?(previous|prior|above) instructions",
    r"disregard (all )?(previous|prior|above)",
    r"you are now",
    r"system prompt",
    r"reveal (the )?(system|hidden) prompt",
    r"act as (an? )?(unfiltered|jailbroken|dan)",
    r"pretend (you|there) (are|is) no (rules|restrictions|guardrails)",
]

SENSITIVE_DATA_PATTERNS = [
    r"all customers?('|s)? (phone|email|address|data)",
    r"every customer('|s)? (phone|email|address)",
    r"dump (the )?(database|db|table)",
    r"list all (customers|users|emails|phone numbers)",
    r"select \* from",
    r"drop table",
    r"delete from",
]

UNSAFE_PATTERNS = [
    r"\bhack\b", r"\bexploit\b.*\bvulnerab", r"credit card number", r"social security",
]

MAX_INPUT_CHARS = 4000


@dataclass
class GuardrailResult:
    allowed: bool
    reason: str = ""
    category: str = ""


def _match_any(patterns: list[str], text: str) -> str | None:
    low = text.lower()
    for p in patterns:
        if re.search(p, low):
            return p
    return None


def check_input(text: str) -> GuardrailResult:
    if not text or not text.strip():
        return GuardrailResult(False, "Empty input.", "invalid_input")
    if len(text) > MAX_INPUT_CHARS:
        return GuardrailResult(False, "Input too large.", "invalid_input")
    if _match_any(INJECTION_PATTERNS, text):
        return GuardrailResult(False, "This looks like an attempt to override my instructions, so I can't act on it.", "prompt_injection")
    if _match_any(SENSITIVE_DATA_PATTERNS, text):
        return GuardrailResult(False, "I can't provide bulk or other customers' data - only your own account information.", "sensitive_data_request")
    if _match_any(UNSAFE_PATTERNS, text):
        return GuardrailResult(False, "I can't help with that request.", "unsafe_request")
    return GuardrailResult(True)


# ---------------------------------------------------------------------------
# Output PII patterns — each entry is (regex, label) for precise detection.
#
# Design rules:
#   Phone   – require formatting characters (space/dash/+) so bare digit
#             sequences in order amounts or tracking IDs don't false-fire.
#   Email   – one email in the reply is likely the customer's own account;
#             two or more suggests bulk data exposure.
#   Card    – full 16-digit 4-4-4-4 grouped pattern only (old pattern was
#             12-digit which hit tracking numbers and was still wrong for cards).
# ---------------------------------------------------------------------------
_PII_PATTERNS: list[tuple[str, str]] = [
    # Phone — international (+91 98765 43210) or formatted local (98765-43210 / 123.456.7890)
    (r"\+\d{1,3}[\s\-]\d{3,5}[\s\-]\d{3,5}(?:[\s\-]\d{2,4})?", "phone_international"),
    (r"\b\d{3}[\s\-\.]\d{3}[\s\-\.]\d{4}\b",                    "phone_us_format"),
    (r"\b\d{5}[\s\-]\d{5}\b",                                    "phone_in_format"),

    # Credit / debit card — exactly 16 digits in 4-4-4-4 groups (spaces or dashes)
    (r"\b\d{4}[\s\-]\d{4}[\s\-]\d{4}[\s\-]\d{4}\b",             "card_number"),
]

# Compiled once at import time for speed
_COMPILED_PII = [(re.compile(p), label) for p, label in _PII_PATTERNS]
_EMAIL_RE     = re.compile(r"\b[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}\b")

# Showing one email (e.g. the customer's own) is fine; 2+ signals a data dump
_EMAIL_LEAK_THRESHOLD = 2


def check_output(text: str) -> GuardrailResult:
    """Output guardrail: block accidental PII leakage in agent responses.

    Checks:
      1. Formatted phone numbers  – international or local style only.
      2. Full 16-digit card numbers in 4-4-4-4 grouping.
      3. Two or more distinct email addresses (single = likely the customer's own).
    """
    # Check phone / card patterns
    for pattern, label in _COMPILED_PII:
        if pattern.search(text):
            return GuardrailResult(
                False,
                "Response withheld: it appears to contain personal data that shouldn't be shared this way.",
                "pii_leak",
            )

    # Check for email exposure (PII leak)
    emails_found = _EMAIL_RE.findall(text)
    if emails_found:
        return GuardrailResult(
            False,
            "Response withheld: it appears to contain personal data that shouldn't be shared this way.",
            "pii_leak",
        )

    return GuardrailResult(True)
