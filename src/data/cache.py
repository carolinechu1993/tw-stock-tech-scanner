from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd


class ParquetCache:
    def __init__(self, cache_dir: str, ttl_minutes: int = 60):
        self.dir = Path(cache_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.ttl = timedelta(minutes=ttl_minutes)

    def _path(self, symbol: str) -> Path:
        safe = symbol.replace("/", "_")
        return self.dir / f"{safe}.parquet"

    def load(self, symbol: str) -> pd.DataFrame | None:
        p = self._path(symbol)
        if not p.exists():
            return None
        mtime = datetime.fromtimestamp(p.stat().st_mtime)
        if datetime.now() - mtime > self.ttl:
            return None
        return pd.read_parquet(p)

    def save(self, symbol: str, df: pd.DataFrame) -> None:
        df.to_parquet(self._path(symbol))
