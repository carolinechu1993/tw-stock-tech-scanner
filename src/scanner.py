from pathlib import Path
from typing import List
import yaml
import pandas as pd

from .data.yfinance_src import YFinanceSource
from .data.cache import ParquetCache
from .signals.scoring import evaluate, score, to_dataframe


def load_config(path: str | Path = "config.yaml") -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_data_source(cfg: dict, force_refresh: bool = False) -> YFinanceSource:
    cache = ParquetCache(cfg["data"]["cache_dir"], ttl_minutes=60)
    if cfg["data"]["source"] == "yfinance":
        return YFinanceSource(cache, force_refresh=force_refresh)
    raise ValueError(f"Unsupported data source: {cfg['data']['source']}")


def _process_history(df: pd.DataFrame, sym: str, name: str, cfg: dict):
    """Compute indicators+score for one stock. Returns (row_dict, results_or_none)."""
    if df is None or len(df) < 30:
        return ({"symbol": sym, "name": name,
                 "error": "no data" if df is None else "insufficient history",
                 "hits": 0}, None)
    try:
        results = evaluate(df, cfg["indicators"], cfg["rules"])
        sc = score(results, cfg["rules"])
        last = df.iloc[-1]
        row = {
            "symbol": sym, "name": name,
            "close": round(float(last["close"]), 2),
            "volume": int(last["volume"]),
            "as_of": df.index[-1].strftime("%Y-%m-%d"),
            **sc,
        }
        return (row, results)
    except Exception as e:
        return ({"symbol": sym, "name": name, "error": str(e), "hits": 0}, None)


def _resolve_universe(cfg: dict, universe_or_key) -> List[dict]:
    """Accept either a universe key (str, looked up in config) or a list of dicts."""
    if isinstance(universe_or_key, str):
        return cfg["universe"][universe_or_key]
    return universe_or_key


def scan(cfg: dict, universe_or_key="test_10", force_refresh: bool = False) -> pd.DataFrame:
    src = build_data_source(cfg, force_refresh=force_refresh)
    universe = _resolve_universe(cfg, universe_or_key)
    days = cfg["data"]["history_days"]
    symbols = [item["symbol"] for item in universe]
    histories = src.get_history_batch(symbols, days)
    rows = []
    for item in universe:
        sym = item["symbol"]
        name = item.get("name", sym)
        row, _ = _process_history(histories.get(sym), sym, name, cfg)
        rows.append(row)
    return to_dataframe(rows)


def scan_with_details(cfg: dict, universe_or_key="test_10", force_refresh: bool = False):
    """Same as scan() but also returns dict of {symbol -> (df, results)} for UI drill-down.

    `universe_or_key` accepts either:
    - str: a key in cfg["universe"] (e.g. "test_10", "semiconductor")
    - list[dict]: a dynamic universe with items {"symbol": ..., "name": ...}
    """
    src = build_data_source(cfg, force_refresh=force_refresh)
    universe = _resolve_universe(cfg, universe_or_key)
    days = cfg["data"]["history_days"]
    symbols = [item["symbol"] for item in universe]
    histories = src.get_history_batch(symbols, days)
    rows = []
    details = {}
    for item in universe:
        sym = item["symbol"]
        name = item.get("name", sym)
        df = histories.get(sym)
        row, results = _process_history(df, sym, name, cfg)
        rows.append(row)
        if results is not None:
            details[sym] = (df, results)
    return to_dataframe(rows), details


if __name__ == "__main__":
    import sys
    cfg = load_config()
    universe_key = sys.argv[1] if len(sys.argv) > 1 else "test_10"
    df = scan(cfg, universe_key)
    out_cols = ["symbol", "name", "close", "as_of", "hits", "hit_rules"]
    available = [c for c in out_cols if c in df.columns]
    print(df[available].to_string(index=False))
    out_path = Path("cache") / f"ranking_{universe_key}.csv"
    df.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"\nSaved to {out_path}")
