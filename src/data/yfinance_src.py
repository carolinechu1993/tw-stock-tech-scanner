from typing import Optional
import pandas as pd
import yfinance as yf

from .base import DataSource
from .cache import ParquetCache


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
        df = df.rename(columns=str.lower)
        df = df[["open", "high", "low", "close", "volume"]].copy()
        df.index = pd.to_datetime(df.index).tz_localize(None)
        df = df.dropna()

        if self.cache:
            self.cache.save(symbol, df)
        return df.tail(days)

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
