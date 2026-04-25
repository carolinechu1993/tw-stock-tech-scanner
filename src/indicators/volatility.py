import pandas as pd


def bbands(close: pd.Series, period: int = 20, std: float = 2.0) -> pd.DataFrame:
    mid = close.rolling(period, min_periods=period).mean()
    sd = close.rolling(period, min_periods=period).std()
    return pd.DataFrame({
        "mid": mid,
        "upper": mid + std * sd,
        "lower": mid - std * sd,
    })


def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
