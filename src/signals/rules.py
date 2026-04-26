"""Each rule takes (df with OHLCV + indicators) + params, returns (hit: bool, strength: float in [0,1])."""
from dataclasses import dataclass
from typing import Callable, Dict
import pandas as pd

from ..indicators.trend import sma, macd, adx
from ..indicators.momentum import kd_taiwan, rsi
from ..indicators.volume import volume_sma, obv
from ..indicators.volatility import bbands, atr


@dataclass
class RuleResult:
    hit: bool
    strength: float
    detail: str = ""


def _safe_last(s: pd.Series, idx: int = -1):
    try:
        v = s.iloc[idx]
        return None if pd.isna(v) else v
    except (IndexError, KeyError):
        return None


# ---------- Trend ----------

def ma_golden_cross(df: pd.DataFrame, p: dict) -> RuleResult:
    short = sma(df["close"], p["ma"]["short"])
    mid = sma(df["close"], p["ma"]["mid"])
    s_now, s_prev = _safe_last(short), _safe_last(short, -2)
    m_now, m_prev = _safe_last(mid), _safe_last(mid, -2)
    if None in (s_now, s_prev, m_now, m_prev):
        return RuleResult(False, 0.0, "insufficient data")
    crossed = s_prev <= m_prev and s_now > m_now
    spread = (s_now - m_now) / m_now if m_now else 0
    return RuleResult(crossed, min(max(spread * 50, 0), 1) if crossed else 0,
                      f"MA{p['ma']['short']}={s_now:.2f} MA{p['ma']['mid']}={m_now:.2f}")


def macd_hist_turn_positive(df: pd.DataFrame, p: dict) -> RuleResult:
    m = macd(df["close"], p["macd"]["fast"], p["macd"]["slow"], p["macd"]["signal"])
    h_now, h_prev = _safe_last(m["hist"]), _safe_last(m["hist"], -2)
    if None in (h_now, h_prev):
        return RuleResult(False, 0.0, "insufficient data")
    hit = h_prev <= 0 and h_now > 0
    strength = min(abs(h_now) / max(df["close"].iloc[-1] * 0.01, 0.01), 1.0) if hit else 0
    return RuleResult(hit, strength, f"hist {h_prev:.3f}->{h_now:.3f}")


def adx_strong_uptrend(df: pd.DataFrame, p: dict) -> RuleResult:
    a = adx(df["high"], df["low"], df["close"], p["adx"]["period"])
    adx_v = _safe_last(a["adx"])
    plus = _safe_last(a["plus_di"])
    minus = _safe_last(a["minus_di"])
    if None in (adx_v, plus, minus):
        return RuleResult(False, 0.0, "insufficient data")
    hit = adx_v > p["adx"]["threshold"] and plus > minus
    strength = min((adx_v - p["adx"]["threshold"]) / 25, 1.0) if hit else 0
    return RuleResult(hit, strength, f"ADX={adx_v:.1f} +DI={plus:.1f} -DI={minus:.1f}")


# ---------- Momentum ----------

def kd_oversold_golden(df: pd.DataFrame, p: dict) -> RuleResult:
    kd = kd_taiwan(df["high"], df["low"], df["close"], p["kd"]["k_period"])
    k_now, k_prev = _safe_last(kd["k"]), _safe_last(kd["k"], -2)
    d_now, d_prev = _safe_last(kd["d"]), _safe_last(kd["d"], -2)
    if None in (k_now, k_prev, d_now, d_prev):
        return RuleResult(False, 0.0, "insufficient data")
    crossed = k_prev <= d_prev and k_now > d_now
    in_oversold = k_prev < p["kd"]["oversold"] or d_prev < p["kd"]["oversold"]
    hit = crossed and in_oversold
    strength = min((p["kd"]["oversold"] - min(k_prev, d_prev)) / p["kd"]["oversold"], 1.0) if hit else 0
    return RuleResult(hit, max(strength, 0), f"K={k_now:.1f} D={d_now:.1f}")


def rsi_recover(df: pd.DataFrame, p: dict) -> RuleResult:
    r = rsi(df["close"], p["rsi"]["period"])
    rsi_now = _safe_last(r)
    if rsi_now is None:
        return RuleResult(False, 0.0, "insufficient data")
    last5 = r.tail(5).dropna()
    was_oversold = (last5 < p["rsi"]["oversold"]).any()
    hit = was_oversold and rsi_now > p["rsi"]["recover"] and rsi_now < 70
    strength = min((rsi_now - p["rsi"]["recover"]) / 20, 1.0) if hit else 0
    return RuleResult(hit, max(strength, 0), f"RSI={rsi_now:.1f}")


# ---------- Volume ----------

def volume_breakout(df: pd.DataFrame, p: dict) -> RuleResult:
    avg = volume_sma(df["volume"], p["volume"]["avg_period"])
    v_now = _safe_last(df["volume"])
    a_now = _safe_last(avg)
    c_now = _safe_last(df["close"])
    c_prev = _safe_last(df["close"], -2)
    if None in (v_now, a_now, c_now, c_prev) or a_now == 0:
        return RuleResult(False, 0.0, "insufficient data")
    ratio = v_now / a_now
    hit = ratio >= p["volume"]["surge_ratio"] and c_now > c_prev
    strength = min((ratio - p["volume"]["surge_ratio"]) / 2, 1.0) if hit else 0
    return RuleResult(hit, max(strength, 0), f"vol ratio={ratio:.2f}")


def price_volume_surge(df: pd.DataFrame, p: dict) -> RuleResult:
    c_now, c_prev = _safe_last(df["close"]), _safe_last(df["close"], -2)
    v_now, v_prev = _safe_last(df["volume"]), _safe_last(df["volume"], -2)
    if None in (c_now, c_prev, v_now, v_prev) or v_prev == 0:
        return RuleResult(False, 0.0, "insufficient data")
    price_up = c_now > c_prev
    vol_up = v_now > v_prev * 1.1
    hit = price_up and vol_up
    pct = (c_now - c_prev) / c_prev * 100 if c_prev else 0
    return RuleResult(hit, min(pct / 5, 1.0) if hit else 0, f"+{pct:.2f}% vol+{(v_now/v_prev-1)*100:.0f}%")


def obv_new_high(df: pd.DataFrame, p: dict) -> RuleResult:
    o = obv(df["close"], df["volume"])
    lookback = p["obv"]["lookback"]
    if len(o) < lookback + 1:
        return RuleResult(False, 0.0, "insufficient data")
    recent = o.tail(lookback + 1)
    o_now = recent.iloc[-1]
    prior_max = recent.iloc[:-1].max()
    hit = o_now > prior_max
    strength = min((o_now - prior_max) / abs(prior_max) if prior_max else 0, 1.0) if hit else 0
    return RuleResult(hit, max(strength, 0), f"OBV new {lookback}d high")


# ---------- Volatility ----------

def bbands_lower_bounce(df: pd.DataFrame, p: dict) -> RuleResult:
    b = bbands(df["close"], p["bbands"]["period"], p["bbands"]["std"])
    if len(df) < 3:
        return RuleResult(False, 0.0, "insufficient data")
    low_prev = df["low"].iloc[-2]
    lower_prev = b["lower"].iloc[-2]
    c_now = df["close"].iloc[-1]
    c_prev = df["close"].iloc[-2]
    if pd.isna(lower_prev):
        return RuleResult(False, 0.0, "insufficient data")
    touched = low_prev <= lower_prev * 1.005
    bounce = c_now > c_prev and c_now > df["open"].iloc[-1]
    hit = touched and bounce
    return RuleResult(hit, 0.7 if hit else 0,
                      f"low_prev={low_prev:.2f} lower={lower_prev:.2f}")


def bbands_upper_break(df: pd.DataFrame, p: dict) -> RuleResult:
    b = bbands(df["close"], p["bbands"]["period"], p["bbands"]["std"])
    c_now = _safe_last(df["close"])
    upper = _safe_last(b["upper"])
    if None in (c_now, upper):
        return RuleResult(False, 0.0, "insufficient data")
    hit = c_now > upper
    strength = min((c_now - upper) / upper * 20, 1.0) if hit else 0
    return RuleResult(hit, max(strength, 0), f"close={c_now:.2f} upper={upper:.2f}")


def atr_expansion(df: pd.DataFrame, p: dict) -> RuleResult:
    a = atr(df["high"], df["low"], df["close"], p["atr"]["period"])
    if len(a.dropna()) < 20:
        return RuleResult(False, 0.0, "insufficient data")
    a_now = a.iloc[-1]
    a_avg = a.tail(20).mean()
    if pd.isna(a_now) or pd.isna(a_avg) or a_avg == 0:
        return RuleResult(False, 0.0, "insufficient data")
    ratio = a_now / a_avg
    hit = ratio >= p["atr"]["expansion_ratio"]
    return RuleResult(hit, min((ratio - 1) / 0.5, 1.0) if hit else 0,
                      f"ATR ratio={ratio:.2f}")


# ---------- 朱家泓派 — 均線結構 ----------

def ma_bullish_alignment(df: pd.DataFrame, p: dict) -> RuleResult:
    """MA5 > MA10 > MA20 > MA60 且四條皆上揚。"""
    ma5 = sma(df["close"], p["ma"]["short"])
    ma10 = sma(df["close"], p["ma"].get("mid_short", 10))
    ma20 = sma(df["close"], p["ma"]["mid"])
    ma60 = sma(df["close"], p["ma"]["long"])
    cur = [ma5.iloc[-1], ma10.iloc[-1], ma20.iloc[-1], ma60.iloc[-1]]
    prev = [ma5.iloc[-2], ma10.iloc[-2], ma20.iloc[-2], ma60.iloc[-2]] if len(df) >= 2 else [None] * 4
    if any(pd.isna(x) for x in cur + prev):
        return RuleResult(False, 0.0, "insufficient data")
    aligned = cur[0] > cur[1] > cur[2] > cur[3]
    rising = all(c > p_ for c, p_ in zip(cur, prev))
    hit = aligned and rising
    return RuleResult(
        hit, 0.8 if hit else 0,
        f"MA5={cur[0]:.1f} MA10={cur[1]:.1f} MA20={cur[2]:.1f} MA60={cur[3]:.1f}",
    )


def ma_converge_breakout(df: pd.DataFrame, p: dict) -> RuleResult:
    """MA5/10/20 三條均線糾結（spread<2%）後，今日紅K突破前 5 日高。"""
    ma5 = sma(df["close"], p["ma"]["short"])
    ma10 = sma(df["close"], p["ma"].get("mid_short", 10))
    ma20 = sma(df["close"], p["ma"]["mid"])
    if len(df) < 25 or pd.isna(ma20.iloc[-1]):
        return RuleResult(False, 0.0, "insufficient data")
    spreads = []
    for i in range(-6, -1):
        m = max(ma5.iloc[i], ma10.iloc[i], ma20.iloc[i])
        n = min(ma5.iloc[i], ma10.iloc[i], ma20.iloc[i])
        if pd.isna(m) or n == 0:
            return RuleResult(False, 0.0, "insufficient data")
        spreads.append((m - n) / n * 100)
    converged = all(s < 2.0 for s in spreads)
    today_red = df["close"].iloc[-1] > df["open"].iloc[-1]
    breakout = df["close"].iloc[-1] > df["high"].iloc[-6:-1].max()
    hit = converged and today_red and breakout
    return RuleResult(
        hit, 0.9 if hit else 0,
        f"糾結最大spread={max(spreads):.2f}% 紅K={today_red} 突破={breakout}",
    )


def pullback_holds_ma20(df: pd.DataFrame, p: dict) -> RuleResult:
    """多頭結構（MA20>MA60）中，近 10 日有回檔但收盤從未跌破 MA20。"""
    ma20 = sma(df["close"], p["ma"]["mid"])
    ma60 = sma(df["close"], p["ma"]["long"])
    if len(df) < 61 or pd.isna(ma20.iloc[-1]) or pd.isna(ma60.iloc[-1]):
        return RuleResult(False, 0.0, "insufficient data")
    bullish_struct = ma20.iloc[-1] > ma60.iloc[-1]
    last10 = df.tail(10)
    pullback_pct = (last10["high"].max() - last10["low"].min()) / last10["high"].max()
    has_pullback = pullback_pct > 0.03
    ma20_window = ma20.tail(10)
    holds = (last10["close"].values >= ma20_window.values).all()
    hit = bullish_struct and has_pullback and holds
    return RuleResult(
        hit, 0.7 if hit else 0,
        f"回檔幅度={pullback_pct*100:.1f}% 守月線={holds}",
    )


# ---------- 朱家泓派 — 量價 ----------

def volume_dry_red_surge(df: pd.DataFrame, p: dict) -> RuleResult:
    """前 2-3 日量縮回檔，今日紅K + 站上 MA5 + 量增 ≥ 1.5×。"""
    if len(df) < 7:
        return RuleResult(False, 0.0, "insufficient data")
    ma5 = sma(df["close"], p["ma"]["short"])
    if pd.isna(ma5.iloc[-1]):
        return RuleResult(False, 0.0, "insufficient data")
    avg_vol = volume_sma(df["volume"], 5)
    prev3 = df.iloc[-4:-1]
    avg_prev = avg_vol.iloc[-5:-2]
    if avg_prev.isna().any() or (avg_prev == 0).any():
        return RuleResult(False, 0.0, "insufficient data")
    is_dry = (prev3["volume"].values < avg_prev.values).any()
    declined = (prev3["close"] < prev3["open"]).any()
    today_red = df["close"].iloc[-1] > df["open"].iloc[-1]
    above_ma5 = df["close"].iloc[-1] > ma5.iloc[-1]
    prev_v = df["volume"].iloc[-2]
    vol_surge = df["volume"].iloc[-1] > prev_v * 1.5 if prev_v > 0 else False
    hit = is_dry and declined and today_red and above_ma5 and vol_surge
    ratio = df["volume"].iloc[-1] / max(prev_v, 1)
    return RuleResult(hit, 0.8 if hit else 0,
                      f"今/昨量={ratio:.2f} 站上MA5={above_ma5}")


# ---------- 朱家泓派 — K 線型態 ----------

def long_red_breakout(df: pd.DataFrame, p: dict) -> RuleResult:
    """實體 ≥ ATR × 1.5、紅K、收盤突破前 5 日高。"""
    a = atr(df["high"], df["low"], df["close"], p["atr"]["period"])
    if len(df) < 21 or pd.isna(a.iloc[-1]):
        return RuleResult(False, 0.0, "insufficient data")
    body = df["close"].iloc[-1] - df["open"].iloc[-1]
    is_red = body > 0
    long_body = body >= a.iloc[-1] * 1.5
    breakout = df["close"].iloc[-1] > df["high"].iloc[-6:-1].max()
    hit = is_red and long_body and breakout
    return RuleResult(hit, 0.8 if hit else 0,
                      f"實體={body:.2f} ATR={a.iloc[-1]:.2f}")


def long_lower_shadow(df: pd.DataFrame, p: dict) -> RuleResult:
    """下影線 ≥ 實體 × 2，且出現於下跌段（5 日內走弱或收盤低於 MA20）。"""
    if len(df) < 21:
        return RuleResult(False, 0.0, "insufficient data")
    o, c, h, low = (df["open"].iloc[-1], df["close"].iloc[-1],
                    df["high"].iloc[-1], df["low"].iloc[-1])
    body = abs(c - o)
    body_eff = max(body, 0.01)
    lower_shadow = min(c, o) - low
    long_lower = lower_shadow > 0 and lower_shadow >= body_eff * 2
    declined = df["close"].iloc[-1] < df["close"].iloc[-5]
    ma20_v = sma(df["close"], p["ma"]["mid"]).iloc[-1]
    below_ma20 = (not pd.isna(ma20_v)) and df["close"].iloc[-1] < ma20_v
    hit = long_lower and (declined or below_ma20)
    ratio = lower_shadow / body_eff
    return RuleResult(hit, min(ratio / 4, 1.0) if hit else 0,
                      f"下影/實體={ratio:.1f}")


def doji_or_spinning_top(df: pd.DataFrame, p: dict) -> RuleResult:
    """實體小於高低差 30%，且出現於近 20 日相對高/低位（上下 20%）。"""
    if len(df) < 21:
        return RuleResult(False, 0.0, "insufficient data")
    o, c, h, low = (df["open"].iloc[-1], df["close"].iloc[-1],
                    df["high"].iloc[-1], df["low"].iloc[-1])
    rng = h - low
    if rng == 0:
        return RuleResult(False, 0.0, "no range")
    body_ratio = abs(c - o) / rng
    is_doji = body_ratio < 0.3
    last20 = df["close"].tail(20)
    pct_rank = (last20 < c).sum() / len(last20)
    at_top = pct_rank > 0.8
    at_bottom = pct_rank < 0.2
    hit = is_doji and (at_top or at_bottom)
    loc = "頂部" if at_top else ("底部" if at_bottom else "中段")
    return RuleResult(hit, 0.5 if hit else 0,
                      f"實體比={body_ratio:.2f} 位置={loc}")


def double_bottom(df: pd.DataFrame, p: dict) -> RuleResult:
    """近 30 日內兩低點接近（<5%）、第二低≥第一低、間距≥5日、之後股價反彈。"""
    if len(df) < 31:
        return RuleResult(False, 0.0, "insufficient data")
    recent = df.tail(30)
    lows = recent["low"].values
    closes = recent["close"].values
    local_min = []
    for i in range(2, len(lows) - 2):
        if (lows[i] < lows[i - 1] and lows[i] < lows[i + 1]
                and lows[i] <= lows[i - 2] and lows[i] <= lows[i + 2]):
            local_min.append(i)
    if len(local_min) < 2:
        return RuleResult(False, 0.0, "no two minima")
    i1, i2 = local_min[-2], local_min[-1]
    if i2 - i1 < 5:
        return RuleResult(False, 0.0, "minima too close")
    low1, low2 = lows[i1], lows[i2]
    similar = abs(low2 - low1) / low1 < 0.05
    second_higher = low2 >= low1
    bounced = closes[-1] > low2 * 1.02
    hit = similar and second_higher and bounced
    return RuleResult(hit, 0.7 if hit else 0,
                      f"低1={low1:.1f} 低2={low2:.1f} 反彈={bounced}")


# =============================================
# Bearish (反向 / 出場 / 空頭) Rules — 17 條
# =============================================

# ---------- 趨勢類 反向 ----------

def ma_death_cross(df: pd.DataFrame, p: dict) -> RuleResult:
    """短期均線（MA5）由上往下穿越中期均線（MA20）— 空頭轉折。"""
    short = sma(df["close"], p["ma"]["short"])
    mid = sma(df["close"], p["ma"]["mid"])
    s_now, s_prev = _safe_last(short), _safe_last(short, -2)
    m_now, m_prev = _safe_last(mid), _safe_last(mid, -2)
    if None in (s_now, s_prev, m_now, m_prev):
        return RuleResult(False, 0.0, "insufficient data")
    crossed = s_prev >= m_prev and s_now < m_now
    spread = (m_now - s_now) / m_now if m_now else 0
    return RuleResult(crossed, min(max(spread * 50, 0), 1) if crossed else 0,
                      f"MA{p['ma']['short']}={s_now:.2f} MA{p['ma']['mid']}={m_now:.2f}")


def ma_bearish_alignment(df: pd.DataFrame, p: dict) -> RuleResult:
    """MA5 < MA10 < MA20 < MA60，且四條均線當日值都比前一日低（皆下行）。"""
    ma5 = sma(df["close"], p["ma"]["short"])
    ma10 = sma(df["close"], p["ma"].get("mid_short", 10))
    ma20 = sma(df["close"], p["ma"]["mid"])
    ma60 = sma(df["close"], p["ma"]["long"])
    cur = [ma5.iloc[-1], ma10.iloc[-1], ma20.iloc[-1], ma60.iloc[-1]]
    prev = [ma5.iloc[-2], ma10.iloc[-2], ma20.iloc[-2], ma60.iloc[-2]] if len(df) >= 2 else [None] * 4
    if any(pd.isna(x) for x in cur + prev):
        return RuleResult(False, 0.0, "insufficient data")
    aligned = cur[0] < cur[1] < cur[2] < cur[3]
    falling = all(c < p_ for c, p_ in zip(cur, prev))
    hit = aligned and falling
    return RuleResult(
        hit, 0.8 if hit else 0,
        f"MA5={cur[0]:.1f} MA10={cur[1]:.1f} MA20={cur[2]:.1f} MA60={cur[3]:.1f}",
    )


def ma_converge_breakdown(df: pd.DataFrame, p: dict) -> RuleResult:
    """MA5/10/20 三條均線糾結（spread<2%）後，今日黑K跌破前 5 日低。"""
    ma5 = sma(df["close"], p["ma"]["short"])
    ma10 = sma(df["close"], p["ma"].get("mid_short", 10))
    ma20 = sma(df["close"], p["ma"]["mid"])
    if len(df) < 25 or pd.isna(ma20.iloc[-1]):
        return RuleResult(False, 0.0, "insufficient data")
    spreads = []
    for i in range(-6, -1):
        m = max(ma5.iloc[i], ma10.iloc[i], ma20.iloc[i])
        n = min(ma5.iloc[i], ma10.iloc[i], ma20.iloc[i])
        if pd.isna(m) or n == 0:
            return RuleResult(False, 0.0, "insufficient data")
        spreads.append((m - n) / n * 100)
    converged = all(s < 2.0 for s in spreads)
    today_black = df["close"].iloc[-1] < df["open"].iloc[-1]
    breakdown = df["close"].iloc[-1] < df["low"].iloc[-6:-1].min()
    hit = converged and today_black and breakdown
    return RuleResult(
        hit, 0.9 if hit else 0,
        f"糾結最大spread={max(spreads):.2f}% 黑K={today_black} 跌破={breakdown}",
    )


def rebound_caps_ma20(df: pd.DataFrame, p: dict) -> RuleResult:
    """空頭結構（MA20<MA60）中，近 10 日有反彈但收盤從未突破 MA20。"""
    ma20 = sma(df["close"], p["ma"]["mid"])
    ma60 = sma(df["close"], p["ma"]["long"])
    if len(df) < 61 or pd.isna(ma20.iloc[-1]) or pd.isna(ma60.iloc[-1]):
        return RuleResult(False, 0.0, "insufficient data")
    bearish_struct = ma20.iloc[-1] < ma60.iloc[-1]
    last10 = df.tail(10)
    rebound_pct = (last10["high"].max() - last10["low"].min()) / last10["low"].min()
    has_rebound = rebound_pct > 0.03
    ma20_window = ma20.tail(10)
    capped = (last10["close"].values <= ma20_window.values).all()
    hit = bearish_struct and has_rebound and capped
    return RuleResult(
        hit, 0.7 if hit else 0,
        f"反彈幅度={rebound_pct*100:.1f}% 壓月線={capped}",
    )


def macd_hist_turn_negative(df: pd.DataFrame, p: dict) -> RuleResult:
    """MACD 柱狀圖（DIF − Signal）由正轉負。"""
    m = macd(df["close"], p["macd"]["fast"], p["macd"]["slow"], p["macd"]["signal"])
    h_now, h_prev = _safe_last(m["hist"]), _safe_last(m["hist"], -2)
    if None in (h_now, h_prev):
        return RuleResult(False, 0.0, "insufficient data")
    hit = h_prev >= 0 and h_now < 0
    strength = min(abs(h_now) / max(df["close"].iloc[-1] * 0.01, 0.01), 1.0) if hit else 0
    return RuleResult(hit, strength, f"hist {h_prev:.3f}->{h_now:.3f}")


def adx_strong_downtrend(df: pd.DataFrame, p: dict) -> RuleResult:
    """ADX > 25 且 -DI > +DI（空方力道強於多方）。"""
    a = adx(df["high"], df["low"], df["close"], p["adx"]["period"])
    adx_v = _safe_last(a["adx"])
    plus = _safe_last(a["plus_di"])
    minus = _safe_last(a["minus_di"])
    if None in (adx_v, plus, minus):
        return RuleResult(False, 0.0, "insufficient data")
    hit = adx_v > p["adx"]["threshold"] and minus > plus
    strength = min((adx_v - p["adx"]["threshold"]) / 25, 1.0) if hit else 0
    return RuleResult(hit, strength, f"ADX={adx_v:.1f} +DI={plus:.1f} -DI={minus:.1f}")


# ---------- 動能類 反向 ----------

def kd_overbought_dead(df: pd.DataFrame, p: dict) -> RuleResult:
    """KD 在 70 以上時，K 由上往下穿越 D。"""
    kd = kd_taiwan(df["high"], df["low"], df["close"], p["kd"]["k_period"])
    k_now, k_prev = _safe_last(kd["k"]), _safe_last(kd["k"], -2)
    d_now, d_prev = _safe_last(kd["d"]), _safe_last(kd["d"], -2)
    if None in (k_now, k_prev, d_now, d_prev):
        return RuleResult(False, 0.0, "insufficient data")
    crossed = k_prev >= d_prev and k_now < d_now
    overbought = 100 - p["kd"]["oversold"]  # 70 if oversold=30
    in_overbought = k_prev > overbought or d_prev > overbought
    hit = crossed and in_overbought
    strength = min((max(k_prev, d_prev) - overbought) / overbought, 1.0) if hit else 0
    return RuleResult(hit, max(strength, 0), f"K={k_now:.1f} D={d_now:.1f}")


def rsi_overbought_drop(df: pd.DataFrame, p: dict) -> RuleResult:
    """RSI 近 5 日曾 > 70，目前跌到 < 60。"""
    r = rsi(df["close"], p["rsi"]["period"])
    rsi_now = _safe_last(r)
    if rsi_now is None:
        return RuleResult(False, 0.0, "insufficient data")
    last5 = r.tail(5).dropna()
    was_overbought = (last5 > 70).any()
    hit = was_overbought and rsi_now < 60 and rsi_now > 30
    strength = min((60 - rsi_now) / 20, 1.0) if hit else 0
    return RuleResult(hit, max(strength, 0), f"RSI={rsi_now:.1f}")


# ---------- 量價類 反向 ----------

def volume_breakdown(df: pd.DataFrame, p: dict) -> RuleResult:
    """成交量 ≥ 5 日均量 × 1.5，且收綠（爆量下跌 / 殺出 / 逃命量）。"""
    avg = volume_sma(df["volume"], p["volume"]["avg_period"])
    v_now = _safe_last(df["volume"])
    a_now = _safe_last(avg)
    c_now = _safe_last(df["close"])
    o_now = _safe_last(df["open"])
    if None in (v_now, a_now, c_now, o_now) or a_now == 0:
        return RuleResult(False, 0.0, "insufficient data")
    ratio = v_now / a_now
    hit = ratio >= p["volume"]["surge_ratio"] and c_now < o_now
    strength = min((ratio - p["volume"]["surge_ratio"]) / 2, 1.0) if hit else 0
    return RuleResult(hit, max(strength, 0), f"vol ratio={ratio:.2f}")


def price_volume_collapse(df: pd.DataFrame, p: dict) -> RuleResult:
    """收盤下跌且成交量比前一日增加超過 10%（量增價跌 / 出貨警示）。"""
    c_now, c_prev = _safe_last(df["close"]), _safe_last(df["close"], -2)
    v_now, v_prev = _safe_last(df["volume"]), _safe_last(df["volume"], -2)
    if None in (c_now, c_prev, v_now, v_prev) or v_prev == 0:
        return RuleResult(False, 0.0, "insufficient data")
    price_down = c_now < c_prev
    vol_up = v_now > v_prev * 1.1
    hit = price_down and vol_up
    pct = (c_now - c_prev) / c_prev * 100 if c_prev else 0
    return RuleResult(hit, min(abs(pct) / 5, 1.0) if hit else 0,
                      f"{pct:.2f}% vol+{(v_now/v_prev-1)*100:.0f}%")


def obv_new_low(df: pd.DataFrame, p: dict) -> RuleResult:
    """OBV 創 N 日新低 — 籌碼面持續流出。"""
    o = obv(df["close"], df["volume"])
    lookback = p["obv"]["lookback"]
    if len(o) < lookback + 1:
        return RuleResult(False, 0.0, "insufficient data")
    recent = o.tail(lookback + 1)
    o_now = recent.iloc[-1]
    prior_min = recent.iloc[:-1].min()
    hit = o_now < prior_min
    strength = min((prior_min - o_now) / abs(prior_min) if prior_min else 0, 1.0) if hit else 0
    return RuleResult(hit, max(strength, 0), f"OBV new {lookback}d low")


def volume_dry_black_surge(df: pd.DataFrame, p: dict) -> RuleResult:
    """前 2-3 日量縮反彈，今日黑K + 跌破 MA5 + 量增 ≥ 前日 1.5 倍（起跌訊號）。"""
    if len(df) < 7:
        return RuleResult(False, 0.0, "insufficient data")
    ma5 = sma(df["close"], p["ma"]["short"])
    if pd.isna(ma5.iloc[-1]):
        return RuleResult(False, 0.0, "insufficient data")
    avg_vol = volume_sma(df["volume"], 5)
    prev3 = df.iloc[-4:-1]
    avg_prev = avg_vol.iloc[-5:-2]
    if avg_prev.isna().any() or (avg_prev == 0).any():
        return RuleResult(False, 0.0, "insufficient data")
    is_dry = (prev3["volume"].values < avg_prev.values).any()
    rebounded = (prev3["close"] > prev3["open"]).any()
    today_black = df["close"].iloc[-1] < df["open"].iloc[-1]
    below_ma5 = df["close"].iloc[-1] < ma5.iloc[-1]
    prev_v = df["volume"].iloc[-2]
    vol_surge = df["volume"].iloc[-1] > prev_v * 1.5 if prev_v > 0 else False
    hit = is_dry and rebounded and today_black and below_ma5 and vol_surge
    ratio = df["volume"].iloc[-1] / max(prev_v, 1)
    return RuleResult(hit, 0.8 if hit else 0,
                      f"今/昨量={ratio:.2f} 跌破MA5={below_ma5}")


# ---------- 波動類 反向 ----------

def bbands_upper_reject(df: pd.DataFrame, p: dict) -> RuleResult:
    """前一日最高觸及/超過布林上軌，今日收黑被壓回。"""
    b = bbands(df["close"], p["bbands"]["period"], p["bbands"]["std"])
    if len(df) < 3:
        return RuleResult(False, 0.0, "insufficient data")
    high_prev = df["high"].iloc[-2]
    upper_prev = b["upper"].iloc[-2]
    c_now = df["close"].iloc[-1]
    o_now = df["open"].iloc[-1]
    if pd.isna(upper_prev):
        return RuleResult(False, 0.0, "insufficient data")
    touched = high_prev >= upper_prev * 0.995
    rejected = c_now < o_now
    hit = touched and rejected
    return RuleResult(hit, 0.7 if hit else 0,
                      f"high_prev={high_prev:.2f} upper={upper_prev:.2f}")


def bbands_lower_break(df: pd.DataFrame, p: dict) -> RuleResult:
    """收盤跌破布林下軌（跌深加速訊號）。"""
    b = bbands(df["close"], p["bbands"]["period"], p["bbands"]["std"])
    c_now = _safe_last(df["close"])
    lower = _safe_last(b["lower"])
    if None in (c_now, lower):
        return RuleResult(False, 0.0, "insufficient data")
    hit = c_now < lower
    strength = min((lower - c_now) / lower * 20, 1.0) if hit else 0
    return RuleResult(hit, max(strength, 0), f"close={c_now:.2f} lower={lower:.2f}")


# ---------- 型態類 反向 ----------

def long_black_breakdown(df: pd.DataFrame, p: dict) -> RuleResult:
    """實體 ≥ ATR × 1.5、黑K、收盤跌破前 5 日最低。"""
    a = atr(df["high"], df["low"], df["close"], p["atr"]["period"])
    if len(df) < 21 or pd.isna(a.iloc[-1]):
        return RuleResult(False, 0.0, "insufficient data")
    body = df["close"].iloc[-1] - df["open"].iloc[-1]
    is_black = body < 0
    long_body = abs(body) >= a.iloc[-1] * 1.5
    breakdown = df["close"].iloc[-1] < df["low"].iloc[-6:-1].min()
    hit = is_black and long_body and breakdown
    return RuleResult(hit, 0.8 if hit else 0,
                      f"實體={body:.2f} ATR={a.iloc[-1]:.2f}")


def long_upper_shadow(df: pd.DataFrame, p: dict) -> RuleResult:
    """上影線 ≥ 實體 × 2，且出現於上漲段（5 日內走強或收盤高於 MA20）。"""
    if len(df) < 21:
        return RuleResult(False, 0.0, "insufficient data")
    o, c, h, low = (df["open"].iloc[-1], df["close"].iloc[-1],
                    df["high"].iloc[-1], df["low"].iloc[-1])
    body = abs(c - o)
    body_eff = max(body, 0.01)
    upper_shadow = h - max(c, o)
    long_upper = upper_shadow > 0 and upper_shadow >= body_eff * 2
    advanced = df["close"].iloc[-1] > df["close"].iloc[-5]
    ma20_v = sma(df["close"], p["ma"]["mid"]).iloc[-1]
    above_ma20 = (not pd.isna(ma20_v)) and df["close"].iloc[-1] > ma20_v
    hit = long_upper and (advanced or above_ma20)
    ratio = upper_shadow / body_eff
    return RuleResult(hit, min(ratio / 4, 1.0) if hit else 0,
                      f"上影/實體={ratio:.1f}")


def double_top(df: pd.DataFrame, p: dict) -> RuleResult:
    """近 30 日內兩高點接近（<5%）、第二高 ≤ 第一高、間距 ≥ 5 日、之後股價回落 ≥ 2%（M 頭）。"""
    if len(df) < 31:
        return RuleResult(False, 0.0, "insufficient data")
    recent = df.tail(30)
    highs = recent["high"].values
    closes = recent["close"].values
    local_max = []
    for i in range(2, len(highs) - 2):
        if (highs[i] > highs[i - 1] and highs[i] > highs[i + 1]
                and highs[i] >= highs[i - 2] and highs[i] >= highs[i + 2]):
            local_max.append(i)
    if len(local_max) < 2:
        return RuleResult(False, 0.0, "no two maxima")
    i1, i2 = local_max[-2], local_max[-1]
    if i2 - i1 < 5:
        return RuleResult(False, 0.0, "maxima too close")
    high1, high2 = highs[i1], highs[i2]
    similar = abs(high2 - high1) / high1 < 0.05
    second_lower = high2 <= high1
    declined = closes[-1] < high2 * 0.98
    hit = similar and second_lower and declined
    return RuleResult(hit, 0.7 if hit else 0,
                      f"高1={high1:.1f} 高2={high2:.1f} 回落={declined}")


RULES: Dict[str, Callable[[pd.DataFrame, dict], RuleResult]] = {
    # 多頭（Bullish）
    "ma_golden_cross": ma_golden_cross,
    "ma_bullish_alignment": ma_bullish_alignment,
    "ma_converge_breakout": ma_converge_breakout,
    "pullback_holds_ma20": pullback_holds_ma20,
    "macd_hist_turn_positive": macd_hist_turn_positive,
    "adx_strong_uptrend": adx_strong_uptrend,
    "kd_oversold_golden": kd_oversold_golden,
    "rsi_recover": rsi_recover,
    "volume_breakout": volume_breakout,
    "price_volume_surge": price_volume_surge,
    "obv_new_high": obv_new_high,
    "volume_dry_red_surge": volume_dry_red_surge,
    "bbands_lower_bounce": bbands_lower_bounce,
    "bbands_upper_break": bbands_upper_break,
    "atr_expansion": atr_expansion,  # 雙向通用
    "long_red_breakout": long_red_breakout,
    "long_lower_shadow": long_lower_shadow,
    "doji_or_spinning_top": doji_or_spinning_top,  # 雙向通用
    "double_bottom": double_bottom,
    # 空頭（Bearish）
    "ma_death_cross": ma_death_cross,
    "ma_bearish_alignment": ma_bearish_alignment,
    "ma_converge_breakdown": ma_converge_breakdown,
    "rebound_caps_ma20": rebound_caps_ma20,
    "macd_hist_turn_negative": macd_hist_turn_negative,
    "adx_strong_downtrend": adx_strong_downtrend,
    "kd_overbought_dead": kd_overbought_dead,
    "rsi_overbought_drop": rsi_overbought_drop,
    "volume_breakdown": volume_breakdown,
    "price_volume_collapse": price_volume_collapse,
    "obv_new_low": obv_new_low,
    "volume_dry_black_surge": volume_dry_black_surge,
    "bbands_upper_reject": bbands_upper_reject,
    "bbands_lower_break": bbands_lower_break,
    "long_black_breakdown": long_black_breakdown,
    "long_upper_shadow": long_upper_shadow,
    "double_top": double_top,
}
