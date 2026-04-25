import numpy as np
import pandas as pd


def volume_sma(volume: pd.Series, period: int = 5) -> pd.Series:
    return volume.rolling(period, min_periods=period).mean()


def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    direction = np.sign(close.diff()).fillna(0)
    return (direction * volume).cumsum()
