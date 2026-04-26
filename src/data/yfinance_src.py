from typing import Optional, Callable
import time
import pandas as pd
import yfinance as yf

from .base import DataSource
from .cache import ParquetCache

# Avoid hammering yfinance with too many tickers per request
BATCH_SIZE = 50
BATCH_SLEEP_SEC = 1.0


def _normalize_ohlcv(df: pd.DataFrame, days: int) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).lower() for c in df.columns]
    if not {"open", "high", "low", "close", "volume"}.issubset(df.columns):
        raise ValueError("missing OHLCV columns")
    df = df[["open", "high", "low", "close", "volume"]]
    df.index = pd.to_datetime(df.index).tz_localize(None)
    df = df.dropna()
    return df.tail(days)


class YFinanceSource(DataSource):
    def __init__(self, cache: ParquetCache | None = None, force_refresh: bool = False,
                 progress_cb: Optional[Callable[[int, int], None]] = None):
        self.cache = cache
        self.force_refresh = force_refresh
        # progress_cb(done, total) — called after each batch finishes
        self.progress_cb = progress_cb

    def get_history(self, symbol: str, days: int) -> pd.DataFrame:
        if self.cache and not self.force_refresh:
            cached = self.cache.load(symbol)
            if cached is not None and len(cached) >= days * 0.6:
                return cached.tail(days)

        period = f"{max(days, 90)}d"
        df = yf.download(
            symbol,
            period=period,
            interval="1d",
            auto_adjust=False,
            progress=False,
            threads=False,
        )
        if df.empty:
            raise ValueError(f"No data returned for {symbol}")

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = _normalize_ohlcv(df, days)
        if self.cache:
            self.cache.save(symbol, df)
        return df

    def _process_batch_result(self, df: pd.DataFrame, batch_symbols: list[str],
                              days: int, out: dict[str, pd.DataFrame]) -> None:
        if df is None or df.empty:
            return
        if len(batch_symbols) == 1:
            sym = batch_symbols[0]
            try:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                normalized = _normalize_ohlcv(df, days)
                if not normalized.empty:
                    out[sym] = normalized
                    if self.cache:
                        self.cache.save(sym, normalized)
            except Exception:
                pass
        else:
            top_levels = (set(df.columns.get_level_values(0))
                          if isinstance(df.columns, pd.MultiIndex) else set())
            for sym in batch_symbols:
                if sym not in top_levels:
                    continue
                try:
                    sub = df[sym]
                    normalized = _normalize_ohlcv(sub, days)
                    if not normalized.empty:
                        out[sym] = normalized
                        if self.cache:
                            self.cache.save(sym, normalized)
                except Exception:
                    continue

    def get_history_batch(self, symbols: list[str], days: int) -> dict[str, pd.DataFrame]:
        out: dict[str, pd.DataFrame] = {}
        miss: list[str] = []

        if self.cache and not self.force_refresh:
            for s in symbols:
                cached = self.cache.load(s)
                if cached is not None and len(cached) >= days * 0.6:
                    out[s] = cached.tail(days)
                else:
                    miss.append(s)
        else:
            miss = list(symbols)

        total = len(miss)
        if self.progress_cb:
            self.progress_cb(len(out), len(symbols))

        if not miss:
            return out

        period = f"{max(days, 90)}d"
        # Split into batches to avoid yfinance throttling
        for batch_start in range(0, total, BATCH_SIZE):
            batch = miss[batch_start:batch_start + BATCH_SIZE]
            try:
                df = yf.download(
                    " ".join(batch),
                    period=period,
                    interval="1d",
                    auto_adjust=False,
                    progress=False,
                    threads=True,
                    group_by="ticker",
                )
                self._process_batch_result(df, batch, days, out)
            except Exception:
                pass  # individual batch failure ok; reflected as missing keys
            if self.progress_cb:
                self.progress_cb(len(out), len(symbols))
            # Sleep between batches (skip after last)
            if batch_start + BATCH_SIZE < total:
                time.sleep(BATCH_SLEEP_SEC)

        return out

    def get_realtime(self, symbol: str) -> Optional[dict]:
        try:
            t = yf.Ticker(symbol)
            info = t.fast_info
            return {
                "price": float(info["last_price"]),
                "volume": int(info.get("last_volume", 0) or 0),
                "ts": pd.Timestamp.now(),
            }
        except Exception:
            return None
