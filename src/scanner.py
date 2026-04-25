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


def scan(cfg: dict, universe_key: str = "test", force_refresh: bool = False) -> pd.DataFrame:
    src = build_data_source(cfg, force_refresh=force_refresh)
    universe: List[dict] = cfg["universe"][universe_key]
    days = cfg["data"]["history_days"]
    rows = []
    for item in universe:
        sym = item["symbol"]
        name = item.get("name", sym)
        try:
            df = src.get_history(sym, days)
            if len(df) < 30:
                rows.append({"symbol": sym, "name": name, "error": "insufficient history",
                             "hits": 0, "weighted_score": 0.0})
                continue
            results = evaluate(df, cfg["indicators"], cfg["rules"])
            sc = score(results, cfg["rules"])
            last = df.iloc[-1]
            rows.append({
                "symbol": sym,
                "name": name,
                "close": round(float(last["close"]), 2),
                "volume": int(last["volume"]),
                "as_of": df.index[-1].strftime("%Y-%m-%d"),
                **sc,
            })
        except Exception as e:
            rows.append({"symbol": sym, "name": name, "error": str(e),
                         "hits": 0, "weighted_score": 0.0})
    return to_dataframe(rows)


def scan_with_details(cfg: dict, universe_key: str = "test", force_refresh: bool = False):
    """Same as scan() but also returns dict of {symbol -> (df, results)} for UI drill-down."""
    src = build_data_source(cfg, force_refresh=force_refresh)
    universe: List[dict] = cfg["universe"][universe_key]
    days = cfg["data"]["history_days"]
    rows = []
    details = {}
    for item in universe:
        sym = item["symbol"]
        name = item.get("name", sym)
        try:
            df = src.get_history(sym, days)
            if len(df) < 30:
                continue
            results = evaluate(df, cfg["indicators"], cfg["rules"])
            sc = score(results, cfg["rules"])
            last = df.iloc[-1]
            rows.append({
                "symbol": sym, "name": name,
                "close": round(float(last["close"]), 2),
                "volume": int(last["volume"]),
                "as_of": df.index[-1].strftime("%Y-%m-%d"),
                **sc,
            })
            details[sym] = (df, results)
        except Exception as e:
            rows.append({"symbol": sym, "name": name, "error": str(e),
                         "hits": 0, "weighted_score": 0.0})
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
