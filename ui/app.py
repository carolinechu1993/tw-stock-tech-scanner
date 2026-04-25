import sys
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.scanner import load_config, scan_with_details
from src.indicators.trend import sma, macd
from src.indicators.momentum import kd_taiwan, rsi
from src.indicators.volatility import bbands
from src.signals.labels import (
    RULE_LABELS, CATEGORY_LABELS, SCHOOL_LABELS,
    rule_zh, cat_zh, school_zh, rule_desc,
)


def get_schools(cfg, rule_id):
    return cfg["rules"].get(rule_id, {}).get("schools", ["general"])


def school_badge(schools):
    return " + ".join(school_zh(s) for s in schools)

st.set_page_config(
    page_title="台股技術分析掃描",
    layout="wide",
    initial_sidebar_state="auto",
)

# ---------- Mobile-friendly CSS ----------
st.markdown(
    """
<style>
.block-container { padding-top: 1rem !important; padding-bottom: 2rem; }
h1 { margin-bottom: 0.4rem; font-size: 1.6rem; }
@media (max-width: 768px) {
  .block-container { padding-left: 0.6rem !important; padding-right: 0.6rem !important; }
  h1 { font-size: 1.3rem; }
  h2 { font-size: 1.05rem; }
  h3 { font-size: 0.95rem; }
  [data-testid="stSidebar"] { min-width: 260px !important; }
  .stTabs [data-baseweb="tab"] { padding: 0.4rem 0.6rem; font-size: 0.9rem; }
}
.stDataFrame { font-size: 0.85rem; }
.disclaimer-banner {
  background:#fff5f5; border-left:3px solid #ff4b4b;
  padding:0.4rem 0.7rem; border-radius:4px;
  font-size:0.78rem; color:#666; line-height:1.4;
  margin-bottom:0.6rem;
}
</style>
    """,
    unsafe_allow_html=True,
)

cfg_static = load_config(ROOT / "config.yaml")

st.title("台股技術分析掃描器")

st.markdown(
    "<div class='disclaimer-banner'>"
    "⚠️ <b>免責聲明</b>：技術分析教學輔助，資料延遲 15-20 分鐘、"
    "<b>非投資建議</b>，盈虧自負。詳細說明見「📖 說明」分頁與頁尾。"
    "</div>",
    unsafe_allow_html=True,
)

CAT_ORDER = ["trend", "momentum", "volume", "volatility", "pattern"]

# ---------- Sidebar ----------

universe_zh_map = {
    "test_10": "測試組（10 檔大型權值）",
    "semiconductor": "半導體族群",
    "shipping": "航運族群",
    "finance": "金融股",
    "ai_server": "AI 伺服器族群",
    "popular_short": "短線熱門股",
    "etf_0050_top20": "0050 前 20 大成分股",
}

if "force_counter" not in st.session_state:
    st.session_state.force_counter = 0

def _chk_key(rid):
    return f"chk_{rid}"


for rid in RULE_LABELS:
    k = _chk_key(rid)
    if k not in st.session_state:
        st.session_state[k] = cfg_static["rules"].get(rid, {}).get("enabled", True)


def _set_selection(predicate):
    for rid in RULE_LABELS:
        st.session_state[_chk_key(rid)] = predicate(rid)


def reset_to_default():
    _set_selection(lambda rid: cfg_static["rules"][rid].get("enabled", True))


def select_all():
    _set_selection(lambda rid: True)


def deselect_all():
    _set_selection(lambda rid: False)


def select_school(school):
    _set_selection(lambda rid: school in get_schools(cfg_static, rid))


with st.sidebar:
    st.header("掃描設定")
    universe_keys = list(cfg_static["universe"].keys())
    universe_key = st.selectbox(
        "股票池",
        universe_keys,
        index=0,
        format_func=lambda k: universe_zh_map.get(k, k),
    )
    n = len(cfg_static["universe"][universe_key])
    st.caption(f"共 {n} 檔")

    col1, col2 = st.columns(2)
    if col1.button("重新計算"):
        st.cache_data.clear()
        st.rerun()
    if col2.button("強制重抓", type="primary"):
        st.cache_data.clear()
        st.session_state.force_counter += 1
        st.rerun()

    st.divider()
    st.subheader("🎛️ 指標選擇")

    st.markdown("**派別套用**")
    sc1, sc2 = st.columns(2)
    sc1.button("綜合派", on_click=select_school, args=("general",),
               use_container_width=True,
               help="選取所有屬於綜合派的規則")
    sc2.button("朱家泓派", on_click=select_school, args=("zhu",),
               use_container_width=True,
               help="選取所有屬於朱家泓派的規則")

    cc1, cc2, cc3 = st.columns(3)
    cc1.button("預設", on_click=reset_to_default, use_container_width=True)
    cc2.button("全選", on_click=select_all, use_container_width=True)
    cc3.button("清空", on_click=deselect_all, use_container_width=True)

    by_cat_sb = {}
    for rid in RULE_LABELS:
        cat = cfg_static["rules"].get(rid, {}).get("category", "")
        by_cat_sb.setdefault(cat, []).append(rid)
    for cat in CAT_ORDER:
        rule_ids = by_cat_sb.get(cat, [])
        if not rule_ids:
            continue
        st.markdown(f"**{cat_zh(cat)}類**")
        for rid in rule_ids:
            schools = get_schools(cfg_static, rid)
            badge = "／".join(school_zh(s).replace("派", "") for s in schools)
            label = f"{rule_zh(rid)}　▸{badge}"
            st.checkbox(label, key=_chk_key(rid))

    n_selected = sum(1 for rid in RULE_LABELS if st.session_state.get(_chk_key(rid), False))
    st.caption(f"已選 {n_selected} / {len(RULE_LABELS)} 條")


# ---------- Scan ----------

@st.cache_data(ttl=600, show_spinner="抓取資料並計算指標中...")
def run_scan(universe_key: str, force_refresh: bool, _cache_buster: int,
             enabled_rules: tuple):
    cfg = load_config(ROOT / "config.yaml")
    enabled_set = set(enabled_rules)
    for rid, rule_cfg in cfg["rules"].items():
        rule_cfg["enabled"] = rid in enabled_set
    return scan_with_details(cfg, universe_key, force_refresh=force_refresh)


enabled_tuple = tuple(
    rid for rid in RULE_LABELS if st.session_state.get(_chk_key(rid), False)
)

if not enabled_tuple:
    st.warning("⚠️ 至少要選一條指標才能掃描，請從左側「指標選擇」勾選。")
    st.stop()

force_now = st.session_state.force_counter > 0
ranking, details = run_scan(
    universe_key, force_now, st.session_state.force_counter, enabled_tuple
)
st.session_state.force_counter = 0

if ranking.empty:
    st.warning("無資料")
    st.stop()


# ---------- Display ranking ----------

def _format_hit_rules(rules):
    return "、".join(rule_zh(r) for r in rules) if rules else "—"


def _format_categories(by_cat):
    return " / ".join(f"{cat_zh(k)}:{v}" for k, v in by_cat.items()) if by_cat else "—"


display_df = ranking.copy()
if "hit_rules" in display_df.columns:
    display_df["命中規則"] = display_df["hit_rules"].apply(
        lambda x: _format_hit_rules(x) if isinstance(x, list) else "—"
    )
if "by_category" in display_df.columns:
    display_df["分類分布"] = display_df["by_category"].apply(
        lambda x: _format_categories(x) if isinstance(x, dict) else "—"
    )

display_df = display_df.rename(columns={
    "symbol": "代號", "name": "名稱", "close": "收盤價",
    "volume": "成交量", "as_of": "資料日", "hits": "命中數",
    "error": "錯誤",
})
cols_order = [c for c in
              ["代號", "名稱", "收盤價", "資料日", "命中數",
               "命中規則", "分類分布", "錯誤"]
              if c in display_df.columns]

scan_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

tab_rank, tab_detail, tab_help = st.tabs(["📊 排行榜", "🔍 個股詳情", "📖 說明"])

# ---------- Tab 1: Ranking ----------

with tab_rank:
    st.caption(
        f"掃描時間：{scan_ts}　|　使用 {len(enabled_tuple)} / {len(RULE_LABELS)} 條規則"
    )
    st.dataframe(display_df[cols_order], width="stretch", hide_index=True)

# ---------- Tab 2: Per-stock detail ----------

with tab_detail:
    selectable = [r for r in ranking["symbol"].tolist() if r in details]
    if not selectable:
        st.info("無可繪製個股")
    else:
        selected = st.selectbox(
            "選擇股票",
            selectable,
            format_func=lambda s: f"{s} {ranking.loc[ranking['symbol']==s, 'name'].iloc[0]}",
        )
        df, results = details[selected]
        ind_p = cfg_static["indicators"]
        rule_cfg = cfg_static["rules"]

        hit_rows = []
        for name, r in results.items():
            cfg_r = rule_cfg.get(name, {})
            desc = rule_desc(name)
            hit_rows.append({
                "規則": rule_zh(name),
                "分類": cat_zh(cfg_r.get("category", "")),
                "命中": "✅" if r.hit else "—",
                "計算說明": r.detail,
                "意義": desc.get("meaning", ""),
            })
        hit_table = pd.DataFrame(hit_rows)
        st.dataframe(hit_table, width="stretch", hide_index=True)

        fig = make_subplots(
            rows=4, cols=1, shared_xaxes=True,
            row_heights=[0.45, 0.18, 0.18, 0.19],
            vertical_spacing=0.04,
            subplot_titles=("K 線 + 均線 + 布林通道", "成交量",
                            "KD（台股 9-3-3）", "MACD"),
        )

        fig.add_trace(go.Candlestick(x=df.index, open=df["open"], high=df["high"],
                                     low=df["low"], close=df["close"], name="K 線",
                                     increasing_line_color="red",
                                     decreasing_line_color="green"),
                      row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=sma(df["close"], ind_p["ma"]["short"]),
                                 name=f"MA{ind_p['ma']['short']}",
                                 line=dict(width=1)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=sma(df["close"], ind_p["ma"]["mid"]),
                                 name=f"MA{ind_p['ma']['mid']}",
                                 line=dict(width=1)), row=1, col=1)
        b = bbands(df["close"], ind_p["bbands"]["period"], ind_p["bbands"]["std"])
        fig.add_trace(go.Scatter(x=df.index, y=b["upper"], name="布林上軌",
                                 line=dict(dash="dot", width=1)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=b["lower"], name="布林下軌",
                                 line=dict(dash="dot", width=1)), row=1, col=1)

        colors = ["red" if c >= o else "green" for c, o in zip(df["close"], df["open"])]
        fig.add_trace(go.Bar(x=df.index, y=df["volume"], name="成交量",
                             marker_color=colors), row=2, col=1)

        kd = kd_taiwan(df["high"], df["low"], df["close"], ind_p["kd"]["k_period"])
        fig.add_trace(go.Scatter(x=df.index, y=kd["k"], name="K 值"), row=3, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=kd["d"], name="D 值"), row=3, col=1)
        fig.add_hline(y=ind_p["kd"]["oversold"], line_dash="dash",
                      line_color="gray", row=3, col=1)

        m = macd(df["close"], ind_p["macd"]["fast"], ind_p["macd"]["slow"],
                 ind_p["macd"]["signal"])
        hist_colors = ["red" if h >= 0 else "green" for h in m["hist"].fillna(0)]
        fig.add_trace(go.Bar(x=df.index, y=m["hist"], name="MACD 柱",
                             marker_color=hist_colors), row=4, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=m["macd"], name="DIF"), row=4, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=m["signal"], name="MACD"), row=4, col=1)

        fig.update_layout(height=600, xaxis_rangeslider_visible=False,
                          showlegend=True,
                          legend=dict(orientation="h", yanchor="bottom", y=1.02,
                                      xanchor="right", x=1, font=dict(size=10)),
                          margin=dict(l=10, r=10, t=50, b=10))
        st.plotly_chart(fig, width="stretch")

# ---------- Tab 3: Help ----------

with tab_help:
    with st.expander("⚠️ 關於資料即時性", expanded=False):
        st.markdown(
            """
- 資料來源：**yfinance**，延遲約 **15–20 分鐘**，並非 tick 即時。
- **盤中（09:00–13:30）抓資料**：當日 K 棒的「收盤價」其實是「當下最後一筆」，會隨盤跳動，
  因此**盤中訊號會反覆成立又失效**，僅供觀察、不建議當作進場依據。
- **建議使用時機**：每日 **14:00 後**抓盤後資料最穩定，當日訊號不會再變動。
- **快取策略**：
  - 「重新計算」：清掉計算結果快取（用本地資料重算指標，~1 秒）
  - 「強制重抓」：清掉本地檔案快取並重打 yfinance（~30 秒，盤中要看最新就用這個）
            """
        )

    with st.expander("📚 指標說明（每條規則的定義、意義、限制）", expanded=False):
        by_cat = {}
        for rid in RULE_LABELS:
            cat = cfg_static["rules"].get(rid, {}).get("category", "")
            by_cat.setdefault(cat, []).append(rid)
        for cat in CAT_ORDER:
            rule_ids = by_cat.get(cat, [])
            if not rule_ids:
                continue
            st.markdown(f"#### {cat_zh(cat)}類")
            for rid in rule_ids:
                desc = rule_desc(rid)
                badge = school_badge(get_schools(cfg_static, rid))
                st.markdown(
                    f"**{rule_zh(rid)}**　"
                    f"<span style='background:#eef;padding:2px 6px;border-radius:6px;"
                    f"font-size:0.75em;color:#446'>{badge}</span>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f"- 怎麼算：{desc['what']}  \n"
                    f"- 代表意義：{desc['meaning']}  \n"
                    f"- 注意事項：{desc['caveat']}"
                )
            st.markdown("")

    with st.expander("📐 數字來源透明說明", expanded=False):
        st.markdown(
            """
**1. 指標參數 — ✅ 產業標準**
源自原作者論文（Wilder 1978、Appel、Lane、Bollinger），所有看盤軟體預設值。
台股 KD 採 9-3-3（國際 Stochastic 多用 14-3-3）。

**2. 進場閾值 — 部分標準、部分啟發式**
- ✅ Wilder 原著：RSI 30/70、ADX > 25
- ⚠️ 台股慣用：KD < 30（國際多用 20，因台股波動大）
- ❌ 啟發式：量能放大 1.5×、ATR 擴張 1.3×

**3. 計分方式 — 純命中數，每條規則平等對待**
本系統不使用權重；排序就是「符合幾條規則」。
真正合理的權重需回測校準，未經校準的主觀權重會誤導，所以暫不加權。

**4. 兩派指標來源**
- **綜合派**（11 條）：MA 黃金交叉、MACD、ADX、KD、RSI、爆量突破、量價齊揚、OBV、布林上下軌、ATR
- **朱家泓派**（8 條）：均線多頭排列、均線糾結突破、回檔不破月線、量縮回檔紅K放量、長紅K突破、長下影線、變盤線、底部第二隻腳

部分規則（KD、爆量突破、量價齊揚）兩派都使用。

→ **本系統是「過濾候選股的篩選器」，不是「保證進場成功的訊號」**。
            """
        )

# ---------- Footer ----------
st.divider()
st.markdown(
    """
<div style='text-align:center; color:#888; font-size:0.85em; line-height:1.6'>
本工具僅供技術分析教學與研究輔助 ・ 資料延遲 15-20 分鐘 ・ <b>非投資建議</b><br>
投資有風險、過往訊號不保證未來績效、使用者須自行承擔投資決策與盈虧責任<br>
資料源：yfinance ・ 指標實作：純 pandas ・ 計分：純命中數（無主觀權重）
</div>
    """,
    unsafe_allow_html=True,
)
