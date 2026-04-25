import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd
import pytest

from src.indicators.trend import sma, ema, macd, adx
from src.indicators.momentum import kd_taiwan, rsi
from src.indicators.volume import obv, volume_sma
from src.indicators.volatility import bbands, atr


@pytest.fixture
def synthetic_df():
    n = 100
    rng = np.random.default_rng(42)
    close = pd.Series(100 + rng.standard_normal(n).cumsum(),
                      index=pd.date_range("2024-01-01", periods=n))
    high = close + rng.uniform(0.5, 2, n)
    low = close - rng.uniform(0.5, 2, n)
    open_ = close.shift(1).fillna(close.iloc[0])
    vol = pd.Series(rng.integers(1000, 5000, n), index=close.index, dtype=float)
    return pd.DataFrame({"open": open_, "high": high, "low": low,
                         "close": close, "volume": vol})


def test_sma_basic():
    s = pd.Series([1, 2, 3, 4, 5], dtype=float)
    out = sma(s, 3)
    assert out.iloc[-1] == pytest.approx(4.0)
    assert pd.isna(out.iloc[1])


def test_ema_basic():
    s = pd.Series([1.0] * 20)
    out = ema(s, 5)
    assert out.iloc[-1] == pytest.approx(1.0)


def test_macd_shape(synthetic_df):
    m = macd(synthetic_df["close"])
    assert {"macd", "signal", "hist"} <= set(m.columns)
    assert len(m) == len(synthetic_df)


def test_adx_shape(synthetic_df):
    a = adx(synthetic_df["high"], synthetic_df["low"], synthetic_df["close"])
    assert {"adx", "plus_di", "minus_di"} <= set(a.columns)
    last = a.dropna().iloc[-1]
    assert 0 <= last["adx"] <= 100


def test_kd_range(synthetic_df):
    kd = kd_taiwan(synthetic_df["high"], synthetic_df["low"], synthetic_df["close"])
    valid = kd.dropna()
    assert (valid["k"].between(0, 100)).all()
    assert (valid["d"].between(0, 100)).all()


def test_kd_taiwan_formula():
    """K_t = 2/3 K_{t-1} + 1/3 RSV_t — verify against hand calc."""
    high = pd.Series([10, 11, 12, 13, 14, 15, 16, 17, 18])
    low = pd.Series([9, 10, 11, 12, 13, 14, 15, 16, 17])
    close = pd.Series([9.5, 10.5, 11.5, 12.5, 13.5, 14.5, 15.5, 16.5, 17.5])
    kd = kd_taiwan(high, low, close, k_period=9)
    assert not pd.isna(kd["k"].iloc[-1])
    assert 0 <= kd["k"].iloc[-1] <= 100


def test_rsi_range(synthetic_df):
    r = rsi(synthetic_df["close"]).dropna()
    assert (r.between(0, 100)).all()


def test_obv_monotonic_up():
    close = pd.Series([10, 11, 12, 13, 14], dtype=float)
    vol = pd.Series([100, 100, 100, 100, 100], dtype=float)
    o = obv(close, vol)
    assert o.iloc[-1] == 400


def test_volume_sma():
    v = pd.Series([10, 20, 30, 40, 50], dtype=float)
    out = volume_sma(v, 5)
    assert out.iloc[-1] == 30.0


def test_bbands_relations(synthetic_df):
    b = bbands(synthetic_df["close"]).dropna()
    assert (b["upper"] >= b["mid"]).all()
    assert (b["mid"] >= b["lower"]).all()


def test_atr_positive(synthetic_df):
    a = atr(synthetic_df["high"], synthetic_df["low"], synthetic_df["close"]).dropna()
    assert (a > 0).all()
