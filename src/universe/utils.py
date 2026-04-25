"""Helpers for parsing user-provided ticker lists (custom universe / watchlist)."""
from __future__ import annotations
import re

MAX_SYMBOLS = 100

_FULLWIDTH_SPACES = "　\xa0"
_SEPARATORS = re.compile(r"[\s,;、。；，]+")


def _normalize(text: str) -> str:
    """Half-width-ize and trim user input."""
    if not text:
        return ""
    out = text.replace("．", ".")
    for ch in _FULLWIDTH_SPACES:
        out = out.replace(ch, " ")
    return out.strip()


def parse_tickers(text: str) -> list[str]:
    """Parse free-text user input into a list of yfinance-compatible Taiwan tickers.

    - Splits on lines/commas/semicolons/Chinese commas
    - 4-digit number → append `.TW` (上市)
    - 5+ digit number → append `.TWO` (上櫃)
    - Already has `.TW` / `.TWO` suffix → keep as-is
    - Strips spaces, dedupes preserving order
    """
    if not text:
        return []
    normalized = _normalize(text)
    raw_tokens = _SEPARATORS.split(normalized)
    out: list[str] = []
    seen: set[str] = set()
    for tok in raw_tokens:
        t = tok.strip().upper()
        if not t:
            continue
        if t.endswith(".TW") or t.endswith(".TWO"):
            sym = t
        elif re.fullmatch(r"\d{4}", t):
            sym = f"{t}.TW"
        elif re.fullmatch(r"\d{5,6}", t):
            sym = f"{t}.TWO"
        else:
            continue  # invalid, skip silently
        if sym not in seen:
            seen.add(sym)
            out.append(sym)
    return out


def validate_tickers(symbols: list[str], limit: int = MAX_SYMBOLS) -> tuple[list[str], bool]:
    """De-dupe & cap. Returns (cleaned_list, was_truncated)."""
    seen: set[str] = set()
    out: list[str] = []
    for s in symbols:
        s = s.strip().upper()
        if s and s not in seen:
            seen.add(s)
            out.append(s)
    truncated = len(out) > limit
    return out[:limit], truncated


def to_universe(symbols: list[str], name_lookup: dict[str, str] | None = None) -> list[dict]:
    """Convert ticker list to scanner-compatible universe items."""
    name_lookup = name_lookup or {}
    return [
        {"symbol": s, "name": name_lookup.get(s, s.replace(".TW", "").replace(".TWO", ""))}
        for s in symbols
    ]
