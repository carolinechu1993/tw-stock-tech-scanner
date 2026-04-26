"""Locate where each rule was triggered along the historical timeseries,
so we can annotate the K-line chart with markers showing each occurrence.

Each function returns a list of dict[date -> price/value used for placement]:
    [{"date": pd.Timestamp, "price": float, "y_offset_axis": "y1"|"y2"|"y3"}, ...]

Plotly uses these to add scatter markers on the appropriate subplot.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

from ..indicators.trend import sma, macd
from ..indicators.momentum import kd_taiwan
from ..indicators.volume import volume_sma


def find_ma_golden_cross(df: pd.DataFrame, p: dict) -> list[dict]:
    """MA5 上穿 MA20 的所有歷史日期。"""
    short = sma(df["close"], p["ma"]["short"])
    mid = sma(df["close"], p["ma"]["mid"])
    out = []
    for i in range(1, len(df)):
        s_now, s_prev = short.iat[i], short.iat[i - 1]
        m_now, m_prev = mid.iat[i], mid.iat[i - 1]
        if pd.isna(s_now) or pd.isna(s_prev) or pd.isna(m_now) or pd.isna(m_prev):
            continue
        if s_prev <= m_prev and s_now > m_now:
            out.append({"date": df.index[i], "price": float(df["low"].iat[i])})
    return out


def find_volume_breakout(df: pd.DataFrame, p: dict) -> list[dict]:
    """成交量爆量突破：vol >= 5MA × 1.5 且當日紅K。"""
    avg = volume_sma(df["volume"], p["volume"]["avg_period"])
    ratio_threshold = p["volume"]["surge_ratio"]
    out = []
    for i in range(len(df)):
        a = avg.iat[i]
        v = df["volume"].iat[i]
        if pd.isna(a) or a == 0:
            continue
        ratio = v / a
        is_red = df["close"].iat[i] > df["open"].iat[i]
        if ratio >= ratio_threshold and is_red:
            out.append({
                "date": df.index[i],
                "volume": float(v),
                "ratio": float(ratio),
            })
    return out


def find_kd_oversold_golden(df: pd.DataFrame, p: dict) -> list[dict]:
    """KD 在 oversold 區黃金交叉。"""
    kd = kd_taiwan(df["high"], df["low"], df["close"], p["kd"]["k_period"])
    oversold = p["kd"]["oversold"]
    out = []
    for i in range(1, len(df)):
        k_now, k_prev = kd["k"].iat[i], kd["k"].iat[i - 1]
        d_now, d_prev = kd["d"].iat[i], kd["d"].iat[i - 1]
        if pd.isna(k_now) or pd.isna(k_prev) or pd.isna(d_now) or pd.isna(d_prev):
            continue
        crossed = k_prev <= d_prev and k_now > d_now
        in_oversold = (k_prev < oversold) or (d_prev < oversold)
        if crossed and in_oversold:
            out.append({"date": df.index[i], "k": float(k_now), "d": float(d_now)})
    return out


def find_bbands_upper_break(df: pd.DataFrame, p: dict) -> list[dict]:
    """收盤突破布林上軌。"""
    from ..indicators.volatility import bbands
    b = bbands(df["close"], p["bbands"]["period"], p["bbands"]["std"])
    out = []
    for i in range(len(df)):
        c = df["close"].iat[i]
        u = b["upper"].iat[i]
        if pd.isna(u):
            continue
        if c > u:
            out.append({"date": df.index[i], "price": float(df["high"].iat[i])})
    return out


def find_long_lower_shadow(df: pd.DataFrame, p: dict) -> list[dict]:
    """下影線 ≥ 實體 × 2，且出現於下跌段。"""
    from ..indicators.trend import sma
    ma20 = sma(df["close"], p["ma"]["mid"])
    out = []
    for i in range(5, len(df)):
        o, c, h, low = (df["open"].iat[i], df["close"].iat[i],
                        df["high"].iat[i], df["low"].iat[i])
        body = abs(c - o)
        body_eff = max(body, 0.01)
        lower_shadow = min(c, o) - low
        if lower_shadow <= 0 or lower_shadow < body_eff * 2:
            continue
        # 下跌段判定
        declined = c < df["close"].iat[i - 5]
        below_ma20 = (not pd.isna(ma20.iat[i])) and c < ma20.iat[i]
        if declined or below_ma20:
            out.append({"date": df.index[i], "price": float(low)})
    return out


def find_double_bottom(df: pd.DataFrame, p: dict) -> list[dict]:
    """W 底兩個低點 + 反彈確認。回傳兩個低點的日期與價位以便連線。"""
    if len(df) < 31:
        return []
    out = []
    # 滑動視窗：以每日為終點，往回看 30 天找 W 底
    # 但這會產生太多重疊，改為：找最後一個有效 W 底
    recent = df.tail(30)
    lows = recent["low"].values
    closes = recent["close"].values
    local_min_idx = []
    for i in range(2, len(lows) - 2):
        if (lows[i] < lows[i - 1] and lows[i] < lows[i + 1]
                and lows[i] <= lows[i - 2] and lows[i] <= lows[i + 2]):
            local_min_idx.append(i)
    if len(local_min_idx) >= 2:
        i1, i2 = local_min_idx[-2], local_min_idx[-1]
        if i2 - i1 >= 5:
            low1, low2 = lows[i1], lows[i2]
            similar = abs(low2 - low1) / low1 < 0.05
            second_higher = low2 >= low1
            bounced = closes[-1] > low2 * 1.02
            if similar and second_higher and bounced:
                out.append({
                    "first_date": recent.index[i1],
                    "first_price": float(low1),
                    "second_date": recent.index[i2],
                    "second_price": float(low2),
                })
    return out


# Marker registry: rule_id -> finder function
MARKER_FINDERS = {
    "ma_golden_cross": find_ma_golden_cross,
    "volume_breakout": find_volume_breakout,
    "kd_oversold_golden": find_kd_oversold_golden,
    "bbands_upper_break": find_bbands_upper_break,
    "long_lower_shadow": find_long_lower_shadow,
    "double_bottom": find_double_bottom,
}


def find_markers(rule_id: str, df: pd.DataFrame, params: dict) -> list[dict]:
    finder = MARKER_FINDERS.get(rule_id)
    if not finder:
        return []
    try:
        return finder(df, params)
    except Exception:
        return []


def supported_rules() -> list[str]:
    return list(MARKER_FINDERS.keys())
