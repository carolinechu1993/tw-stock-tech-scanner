from typing import Optional
import pandas as pd
import yfinance as yf

from .base import DataSource
from .cache import ParquetCache


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
    def __init__(self, cache: ParquetCache | None = None, force_refresh: bool = False):
        self.cache = cache
        self.force_refresh = force_refresh

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

        if not miss:
            return out

        period = f"{max(days, 90)}d"
        try:
            df = yf.download(
                " ".join(miss),
                period=period,
                interval="1d",
                auto_adjust=False,
                progress=False,
                threads=True,
                group_by="ticker",
            )
        except Exception:
            return out

        if df.empty:
            return out

        if len(miss) == 1:
            sym = miss[0]
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
            top_levels = set(df.columns.get_level_values(0)) if isinstance(df.columns, pd.MultiIndex) else set()
            for sym in miss:
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
