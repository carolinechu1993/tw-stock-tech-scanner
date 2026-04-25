from abc import ABC, abstractmethod
from typing import Optional
import pandas as pd


class DataSource(ABC):
    @abstractmethod
    def get_history(self, symbol: str, days: int) -> pd.DataFrame:
        """Return DataFrame indexed by date with columns: open, high, low, close, volume."""

    @abstractmethod
    def get_realtime(self, symbol: str) -> Optional[dict]:
        """Return latest tick: {price, volume, ts}. None if unavailable."""

    def get_history_batch(self, symbols: list[str], days: int) -> dict[str, pd.DataFrame]:
        """Return {symbol: DataFrame}. Missing key = fetch failed for that symbol.

        Default fallback loops over get_history; subclasses should override
        to use real batch endpoints (e.g. yf.download(...) or broker bulk APIs)
        for performance and to avoid per-symbol rate limit consumption.
        """
        out: dict[str, pd.DataFrame] = {}
        for s in symbols:
            try:
                out[s] = self.get_history(s, days)
            except Exception:
                pass
        return out
