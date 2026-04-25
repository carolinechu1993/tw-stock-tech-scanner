import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.universe.utils import parse_tickers, validate_tickers


def test_parse_basic_4digit():
    assert parse_tickers("2330\n2454\n3008") == ["2330.TW", "2454.TW", "3008.TW"]


def test_parse_dedupe_preserve_order():
    assert parse_tickers("2330\n2454\n2330") == ["2330.TW", "2454.TW"]


def test_parse_already_has_suffix():
    assert parse_tickers("2330.TW\n3034.TW") == ["2330.TW", "3034.TW"]


def test_parse_5digit_otc():
    assert parse_tickers("8299\n5347") == ["8299.TW", "5347.TW"]
    assert parse_tickers("80293") == ["80293.TWO"]


def test_parse_with_fullwidth_and_commas():
    assert parse_tickers("2330，2454；3008") == ["2330.TW", "2454.TW", "3008.TW"]


def test_parse_empty_and_whitespace():
    assert parse_tickers("") == []
    assert parse_tickers("   \n  \t  ") == []


def test_parse_invalid_skipped():
    assert parse_tickers("hello\n2330\nabc123") == ["2330.TW"]


def test_parse_mixed_separators():
    assert parse_tickers("2330,2454 3008\n2412") == [
        "2330.TW", "2454.TW", "3008.TW", "2412.TW",
    ]


def test_validate_truncates_at_limit():
    syms = [f"{i:04d}.TW" for i in range(150)]
    out, truncated = validate_tickers(syms, limit=100)
    assert len(out) == 100
    assert truncated is True


def test_validate_no_truncation():
    syms = ["2330.TW", "2454.TW"]
    out, truncated = validate_tickers(syms)
    assert out == syms
    assert truncated is False
