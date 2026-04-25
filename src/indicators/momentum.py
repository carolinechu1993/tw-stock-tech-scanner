import numpy as np
import pandas as pd


def kd_taiwan(high: pd.Series, low: pd.Series, close: pd.Series,
              k_period: int = 9) -> pd.DataFrame:
    """Taiwan-style KD: K_t = 2/3 K_{t-1} + 1/3 RSV_t, D_t = 2/3 D_{t-1} + 1/3 K_t."""
    lowest = low.rolling(k_period, min_periods=k_period).min()
    highest = high.rolling(k_period, min_periods=k_period).max()
    rsv = (close - lowest) / (highest - lowest).replace(0, np.nan) * 100

    k = pd.Series(index=close.index, dtype=float)
    d = pd.Series(index=close.index, dtype=float)
    prev_k, prev_d = 50.0, 50.0
    for i, ts in enumerate(close.index):
        r = rsv.iat[i]
        if pd.isna(r):
            continue
        cur_k = (2 / 3) * prev_k + (1 / 3) * r
        cur_d = (2 / 3) * prev_d + (1 / 3) * cur_k
        k.iat[i] = cur_k
        d.iat[i] = cur_d
        prev_k, prev_d = cur_k, cur_d

    return pd.DataFrame({"k": k, "d": d, "rsv": rsv})


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))
