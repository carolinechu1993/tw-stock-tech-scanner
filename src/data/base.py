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
