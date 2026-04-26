import json
import sys
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

TAIPEI_TZ = ZoneInfo("Asia/Taipei")
WATCHLIST_KEY = "tw_scanner_watchlist_v1"
CUSTOM_TEXT_KEY = "tw_scanner_custom_text_v1"
WATCHLIST_LIMIT = 100

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from streamlit_local_storage import LocalStorage

from src.scanner import load_config, scan_with_details
from src.indicators.trend import sma, macd
from src.indicators.momentum import kd_taiwan, rsi
from src.indicators.volatility import bbands
from src.signals.labels import (
    RULE_LABELS, CATEGORY_LABELS, SCHOOL_LABELS,
    rule_zh, cat_zh, school_zh, rule_desc, rule_summary,
)
from src.signals.markers import find_markers, supported_rules as marker_rules
from src.universe.utils import parse_tickers, validate_tickers, to_universe
from src.universe import dynamic as dyn_univ


def get_schools(cfg, rule_id):
    return cfg["rules"].get(rule_id, {}).get("schools", ["general"])


def school_badge(schools):
    return " + ".join(school_zh(s) for s in schools)


# ---------- LocalStorage helpers ----------

_LS = LocalStorage()


def _init_local_storage():
    """Sync session_state with browser localStorage.

    streamlit-local-storage 的 iframe 載入是 async — 第一次呼叫 getItem 通常回 None，
    要等元件初始化完成才會收到資料。每次 rerun 都嘗試讀，直到讀到非 None 為止。
    每個 getItem/setItem 必須有**唯一 key**，否則多次呼叫會在同一 component slot 互相干擾。
    """
    # 預設值
    if "watchlist" not in st.session_state:
        st.session_state.watchlist = []
    if "custom_text" not in st.session_state:
        st.session_state.custom_text = ""

    # 觀察清單同步：用唯一 key
    if not st.session_state.get("_wl_synced"):
        raw_wl = _LS.getItem(WATCHLIST_KEY, key="get_watchlist")
        if raw_wl is not None:
            try:
                st.session_state.watchlist = json.loads(raw_wl) or []
            except Exception:
                pass
            st.session_state._wl_synced = True

    # 自訂股票文字
    if not st.session_state.get("_text_synced"):
        raw_text = _LS.getItem(CUSTOM_TEXT_KEY, key="get_custom_text")
        if raw_text is not None:
            st.session_state.custom_text = raw_text
            st.session_state._text_synced = True


def save_watchlist():
    """寫入 localStorage — 用每次都不同的 key 確保 component 真的執行。"""
    # 用 watchlist 內容雜湊 + 計數器當 key 後綴，避免「同 key 同 value 不重發」
    counter = st.session_state.get("_save_wl_counter", 0) + 1
    st.session_state["_save_wl_counter"] = counter
    _LS.setItem(
        WATCHLIST_KEY,
        json.dumps(st.session_state.watchlist),
        key=f"set_watchlist_{counter}",
    )


def save_custom_text():
    counter = st.session_state.get("_save_text_counter", 0) + 1
    st.session_state["_save_text_counter"] = counter
    _LS.setItem(
        CUSTOM_TEXT_KEY,
        st.session_state.get("custom_text", ""),
        key=f"set_custom_text_{counter}",
    )

st.set_page_config(
    page_title="台股技術分析掃描",
    layout="wide",
    initial_sidebar_state="auto",
)

# ---------- Responsive CSS (desktop comfort + mobile compact) ----------
st.markdown(
    """
<style>
/* Desktop default (>768px): larger fonts, more breathing room */
.block-container {
  padding-top: 1.2rem !important;
  padding-bottom: 3rem;
  max-width: 1480px;
}
html, body, [class*="st-"] { font-size: 16px; }
h1 { margin-bottom: 0.6rem; font-size: 2rem; }
h2 { font-size: 1.5rem; margin-top: 1.2rem; }
h3 { font-size: 1.2rem; margin-top: 0.9rem; }
h4 { font-size: 1.05rem; margin-top: 0.7rem; }
.stDataFrame { font-size: 1rem; }
.stDataFrame th, .stDataFrame td { padding: 0.6rem 0.8rem !important; }
.stTabs [data-baseweb="tab"] {
  padding: 0.8rem 1.4rem;
  font-size: 1.1rem;
  font-weight: 500;
}
.stTabs [data-baseweb="tab-list"] { gap: 0.3rem; }
.stMarkdown p { line-height: 1.65; }
[data-testid="stSidebar"] [data-testid="stMarkdown"] { font-size: 0.95rem; }
.stCheckbox label { font-size: 0.95rem; }
[data-testid="stDataFrameResizable"] { font-size: 1rem; }
.stSelectbox label, .stMultiSelect label { font-size: 1rem !important; font-weight: 500; }
[data-baseweb="select"] { font-size: 1rem; }
.stCaption, [data-testid="stCaptionContainer"] { font-size: 0.85rem; color: #777; }

/* Mobile (<768px): compact */
@media (max-width: 768px) {
  .block-container { padding-left: 0.6rem !important; padding-right: 0.6rem !important; }
  html, body, [class*="st-"] { font-size: 14px; }
  h1 { font-size: 1.3rem; }
  h2 { font-size: 1.05rem; }
  h3 { font-size: 0.95rem; }
  [data-testid="stSidebar"] { min-width: 260px !important; }
  .stTabs [data-baseweb="tab"] { padding: 0.4rem 0.6rem; font-size: 0.9rem; }
  .stDataFrame { font-size: 0.82rem; }
}

.disclaimer-banner {
  background:#fff5f5; border-left:3px solid #ff4b4b;
  padding:0.5rem 0.9rem; border-radius:4px;
  font-size:0.85rem; color:#666; line-height:1.5;
  margin-bottom:0.8rem;
}
</style>
    """,
    unsafe_allow_html=True,
)

cfg_static = load_config(ROOT / "config.yaml")
_init_local_storage()

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

UNIVERSE_WATCHLIST = "__watchlist__"
UNIVERSE_CUSTOM = "__custom__"

universe_zh_map = {
    "test_10": "測試組（10 檔大型權值）",
    "semiconductor": "半導體族群（精選）",
    "shipping": "航運族群",
    "finance": "金融股",
    "ai_server": "AI 伺服器族群",
    "popular_short": "短線熱門股",
    "etf_0050_top20": "0050 前 20 大成分股",
}


def build_all_universe_options():
    """Group all universe options. Returns list[(key, display_label)]."""
    out: list[tuple[str, str]] = []
    # 預設精選池
    for k in cfg_static["universe"].keys():
        out.append((k, "📦 " + universe_zh_map.get(k, k)))
    # 產業 / 大池（動態，需網路 — TWSE OpenAPI）
    for key, label in dyn_univ.list_groups():
        if key.startswith("all_"):
            out.append((f"dyn:{key}", "🌐 " + label))
        else:
            out.append((f"dyn:{key}", "🏭 " + label))
    # ETF 成分股
    for key, label in dyn_univ.list_etfs():
        out.append((f"etf:{key}", "🪙 " + label))
    # 自訂與觀察清單
    out.append((UNIVERSE_WATCHLIST, "⭐ 我的觀察清單"))
    out.append((UNIVERSE_CUSTOM, "✍️ 自訂股票"))
    return out


def universe_label(k: str) -> str:
    options = build_all_universe_options()
    label_map = {key: label for key, label in options}
    base = label_map.get(k, k)
    # 動態加數量註記
    if k == UNIVERSE_WATCHLIST:
        n = len(st.session_state.get("watchlist", []))
        return f"{base} ({n})"
    if k == UNIVERSE_CUSTOM:
        return base
    return base


def build_universe(universe_key: str):
    """Resolve universe_key into (universe_list, error_message). Error means stop."""
    if universe_key == UNIVERSE_WATCHLIST:
        wl = st.session_state.get("watchlist", [])
        if not wl:
            return None, "⭐ 觀察清單為空，請先從其他股票池掃描後加入。"
        return list(wl), None
    if universe_key == UNIVERSE_CUSTOM:
        raw = st.session_state.get("custom_text", "")
        if not raw.strip():
            return None, "✍️ 請在左側「自訂股票」框中貼入股票代號（一行一檔）。"
        symbols = parse_tickers(raw)
        symbols, truncated = validate_tickers(symbols, limit=WATCHLIST_LIMIT)
        if not symbols:
            return None, "✍️ 沒有有效的股票代號。請確認格式為 4-5 位數字。"
        if truncated:
            st.warning(f"⚠️ 超過 {WATCHLIST_LIMIT} 檔上限，已截斷至 {WATCHLIST_LIMIT} 檔")
        return to_universe(symbols), None
    if universe_key.startswith("dyn:"):
        try:
            universe = dyn_univ.resolve_industry_group(universe_key[4:])
        except Exception as e:
            return None, f"⚠️ 抓取 TWSE 公司清單失敗：{e}"
        if not universe:
            return None, "⚠️ 該分類無資料"
        return universe, None
    if universe_key.startswith("etf:"):
        universe = dyn_univ.resolve_etf(universe_key[4:])
        if not universe:
            return None, "⚠️ 找不到該 ETF 的成分股"
        return universe, None
    return cfg_static["universe"][universe_key], None

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


def select_direction(direction):
    """direction: 'bullish' / 'bearish' — 套用該方向所有規則（包含 neutral 雙向通用）。"""
    from src.signals.labels import RULE_DIRECTION
    _set_selection(lambda rid: RULE_DIRECTION.get(rid, "neutral") in (direction, "neutral"))


with st.sidebar:
    st.header("掃描設定")
    _all_options = build_all_universe_options()
    universe_options = [k for k, _ in _all_options]
    universe_key = st.selectbox(
        "股票池",
        universe_options,
        index=0,
        format_func=universe_label,
        help="📦 精選 / 🏭 產業 / 🌐 全市場 / 🪙 ETF / ⭐ 觀察 / ✍️ 自訂",
        key="universe_select",
    )

    # Custom textarea (only when custom selected)
    if universe_key == UNIVERSE_CUSTOM:
        st.text_area(
            "自訂股票（一行一檔，例：2330 或 2330.TW）",
            key="custom_text",
            height=150,
            placeholder="2330\n2454\n3008",
            help="支援 4-5 位數字代號，自動補 .TW / .TWO 後綴",
            on_change=save_custom_text,
        )
        parsed_count = len(parse_tickers(st.session_state.get("custom_text", "")))
        st.caption(f"已解析 {parsed_count} 檔")
    elif universe_key == UNIVERSE_WATCHLIST:
        wl_n = len(st.session_state.get("watchlist", []))
        st.caption(f"共 {wl_n} 檔")
    elif universe_key.startswith("dyn:") or universe_key.startswith("etf:"):
        # Resolve count without scanning (lookup is fast, cached daily)
        try:
            preview, _ = build_universe(universe_key)
            n = len(preview) if preview else 0
            st.caption(f"共 {n} 檔")
            if n > 200:
                est_min = max(1, ((n + 49) // 50) * 4 // 60)
                st.caption(f"⏱ 首次掃描 ~{est_min} 分鐘（之後有快取秒回）")
        except Exception:
            st.caption("（計算中…）")
    else:
        st.caption(f"共 {len(cfg_static['universe'][universe_key])} 檔")

    col1, col2 = st.columns(2)
    if col1.button("重新計算", key="btn_recompute"):
        st.cache_data.clear()
        st.rerun()
    if col2.button("強制重抓", type="primary", key="btn_force_refresh"):
        st.cache_data.clear()
        st.session_state.force_counter += 1
        st.rerun()

    # ---------- Watchlist management ----------
    st.divider()
    wl = st.session_state.get("watchlist", [])
    with st.expander(f"⭐ 觀察清單管理 ({len(wl)})", expanded=False):
        if not wl:
            st.caption("尚無項目。從排行榜底下選股加入。")
        else:
            for i, item in enumerate(wl):
                c1, c2 = st.columns([4, 1])
                c1.markdown(f"`{item['symbol']}` {item.get('name', '')}")
                if c2.button("✕", key=f"rm_wl_{i}", help="移除"):
                    st.session_state.watchlist.pop(i)
                    save_watchlist()
                    st.rerun()
        st.markdown("---")
        bc1, bc2 = st.columns(2)
        if bc1.button("清空", key="btn_wl_clear",
                      use_container_width=True, disabled=not wl):
            st.session_state.watchlist = []
            save_watchlist()
            st.rerun()
        if wl:
            csv_data = "symbol,name\n" + "\n".join(
                f'{x["symbol"]},{x.get("name","")}' for x in wl
            )
            bc2.download_button(
                "下載 CSV",
                csv_data,
                file_name="watchlist.csv",
                mime="text/csv",
                use_container_width=True,
            )

        uploaded = st.file_uploader("上傳 CSV 還原", type=["csv"], key="wl_upload")
        if uploaded is not None:
            try:
                content = uploaded.read().decode("utf-8-sig")
                imported = []
                seen = set()
                for line in content.strip().splitlines()[1:]:  # skip header
                    parts = line.split(",")
                    if not parts or not parts[0].strip():
                        continue
                    sym = parts[0].strip().upper()
                    name = parts[1].strip() if len(parts) > 1 else sym
                    if sym not in seen:
                        seen.add(sym)
                        imported.append({"symbol": sym, "name": name})
                st.session_state.watchlist = imported[:WATCHLIST_LIMIT]
                save_watchlist()
                st.success(f"已匯入 {len(st.session_state.watchlist)} 檔")
                st.rerun()
            except Exception as e:
                st.error(f"匯入失敗：{e}")

    st.divider()
    st.subheader("🎛️ 指標選擇")

    st.markdown("**派別套用**")
    sc1, sc2 = st.columns(2)
    sc1.button("綜合派", on_click=select_school, args=("general",),
               use_container_width=True, key="btn_school_general",
               help="選取所有屬於綜合派的規則")
    sc2.button("朱家泓派", on_click=select_school, args=("zhu",),
               use_container_width=True, key="btn_school_zhu",
               help="選取所有屬於朱家泓派的規則")

    st.markdown("**方向套用**")
    dc1, dc2 = st.columns(2)
    dc1.button("🔼 多頭訊號", on_click=select_direction, args=("bullish",),
               use_container_width=True, key="btn_dir_bullish",
               help="只勾選多頭/進場規則（含雙向通用）")
    dc2.button("🔽 空頭訊號", on_click=select_direction, args=("bearish",),
               use_container_width=True, key="btn_dir_bearish",
               help="只勾選空頭/出場規則（含雙向通用）")

    cc1, cc2, cc3 = st.columns(3)
    cc1.button("預設", on_click=reset_to_default,
               use_container_width=True, key="btn_rules_default")
    cc2.button("全選", on_click=select_all,
               use_container_width=True, key="btn_rules_all")
    cc3.button("清空", on_click=deselect_all,
               use_container_width=True, key="btn_rules_clear")

    st.divider()
    compact_mode = st.toggle(
        "📱 緊湊模式（手機推薦）",
        value=False,
        help="隱藏「命中規則」與「分類分布」等長文字欄，手機螢幕看更清爽",
    )

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

@st.cache_data(ttl=600, show_spinner=False)
def run_scan(universe_tuple: tuple, force_refresh: bool, _cache_buster: int,
             enabled_rules: tuple):
    cfg = load_config(ROOT / "config.yaml")
    enabled_set = set(enabled_rules)
    for rid, rule_cfg in cfg["rules"].items():
        rule_cfg["enabled"] = rid in enabled_set
    universe = [{"symbol": s, "name": n} for s, n in universe_tuple]
    ranking, details = scan_with_details(cfg, universe, force_refresh=force_refresh)
    scan_ts = datetime.now(TAIPEI_TZ).strftime("%Y-%m-%d %H:%M:%S")
    return ranking, details, scan_ts


enabled_tuple = tuple(
    rid for rid in RULE_LABELS if st.session_state.get(_chk_key(rid), False)
)

if not enabled_tuple:
    st.warning("⚠️ 至少要選一條指標才能掃描，請從左側「指標選擇」勾選。")
    st.stop()

universe_list, universe_err = build_universe(universe_key)
if universe_err:
    st.warning(universe_err)
    st.stop()
universe_tuple = tuple((d["symbol"], d.get("name", d["symbol"])) for d in universe_list)

force_now = st.session_state.force_counter > 0
n_total = len(universe_tuple)
# Empirical: ~3.5s per batch of 50 (yfinance download + 1s sleep + indicator calc)
# Cache hits are near-instant so this is worst-case estimate
batches = (n_total + 49) // 50
est_sec = max(2, batches * 4)
if est_sec < 60:
    eta = f"~{est_sec} 秒"
else:
    minutes = est_sec / 60
    eta = f"~{minutes:.1f} 分鐘" if minutes < 3 else f"~{int(minutes)} 分鐘"
spinner_msg = (
    f"抓取資料並計算指標中（{n_total} 檔，{eta}；有快取則秒回）…"
)
with st.spinner(spinner_msg):
    ranking, details, scan_ts = run_scan(
        universe_tuple, force_now, st.session_state.force_counter, enabled_tuple
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

tab_rank, tab_detail, tab_help = st.tabs(["📊 排行榜", "🔍 個股詳情", "📖 說明"])

# ---------- Tab 1: Ranking ----------

with tab_rank:
    # Compute most common data date for caption
    if "資料日" in display_df.columns and not display_df["資料日"].dropna().empty:
        date_series = display_df["資料日"].dropna()
        mode_date = date_series.mode().iloc[0]
        n_match = int((date_series == mode_date).sum())
        n_total_rows = len(display_df)
        date_caption = (
            f"📅 資料日：{mode_date}"
            + (f" ({n_match}/{n_total_rows} 檔)" if n_match < n_total_rows else "")
        )
    else:
        date_caption = "📅 資料日：—"

    st.caption(
        f"掃描時間：{scan_ts}　|　{date_caption}　|　"
        f"使用 {len(enabled_tuple)} / {len(RULE_LABELS)} 條規則"
        "　|　勾選 ⭐ 即加入觀察清單，取消即移除"
    )
    # Build name lookup (for sync after editing)
    name_lookup = {row["symbol"]: row.get("name", row["symbol"])
                   for _, row in ranking.iterrows() if "symbol" in row}
    existing_syms = {item["symbol"] for item in st.session_state.get("watchlist", [])}

    # Pre-populate ⭐ column
    edit_df = display_df.copy()
    edit_df.insert(0, "⭐", edit_df["代號"].apply(lambda s: s in existing_syms))

    if compact_mode:
        rank_cols = ["⭐"] + [c for c in ["代號", "名稱", "收盤價", "命中數"]
                              if c in edit_df.columns]
    else:
        rank_cols = ["⭐"] + [c for c in cols_order if c != "資料日"]

    rank_col_config = {
        "⭐": st.column_config.CheckboxColumn(
            "⭐",
            help="勾選加入觀察清單；取消移除",
            default=False,
        ),
        "代號": st.column_config.TextColumn("代號", width="small"),
        "名稱": st.column_config.TextColumn("名稱", width="small"),
        "收盤價": st.column_config.NumberColumn("收盤價", width="small", format="%.2f"),
        "資料日": st.column_config.TextColumn("資料日", width="small"),
        "命中數": st.column_config.NumberColumn("命中", width="small"),
        "命中規則": st.column_config.TextColumn("命中規則", width="large"),
        "分類分布": st.column_config.TextColumn("分類分布", width="medium"),
        "錯誤": st.column_config.TextColumn("錯誤", width="medium"),
    }
    edited = st.data_editor(
        edit_df[rank_cols],
        width="stretch",
        hide_index=True,
        column_config={k: v for k, v in rank_col_config.items() if k in rank_cols},
        disabled=[c for c in rank_cols if c != "⭐"],
        key="ranking_editor",
    )

    # Sync watchlist with checkbox state
    new_starred = set(edited.loc[edited["⭐"], "代號"].astype(str))
    old_starred = existing_syms
    if new_starred != old_starred:
        # Preserve order: keep existing watchlist items that are still starred
        current_wl = list(st.session_state.get("watchlist", []))
        kept = [item for item in current_wl if item["symbol"] in new_starred]
        # Append newly starred (not in old)
        for sym in edited.loc[edited["⭐"], "代號"].astype(str):
            if sym not in old_starred and not any(x["symbol"] == sym for x in kept):
                if len(kept) >= WATCHLIST_LIMIT:
                    st.warning(f"⚠️ 觀察清單已達上限 {WATCHLIST_LIMIT} 檔，未加入 {sym}")
                    break
                kept.append({"symbol": sym, "name": name_lookup.get(sym, sym)})
        st.session_state.watchlist = kept
        save_watchlist()
        st.rerun()

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
            hit_rows.append({
                "規則": rule_zh(name),
                "分類": cat_zh(cfg_r.get("category", "")),
                "命中": "✅" if r.hit else "—",
                "意義": rule_summary(name),
            })
        hit_table = pd.DataFrame(hit_rows)
        if compact_mode:
            hit_cols = ["規則", "分類", "命中"]
        else:
            hit_cols = list(hit_table.columns)
        hit_col_config = {
            "規則": st.column_config.TextColumn("規則", width="medium"),
            "分類": st.column_config.TextColumn("分類", width="small"),
            "命中": st.column_config.TextColumn("命中", width="small"),
            "意義": st.column_config.TextColumn("意義", width="medium",
                                                  help="精簡摘要；完整定義請看「📖 說明」分頁"),
        }
        st.dataframe(
            hit_table[hit_cols],
            width="stretch",
            hide_index=True,
            column_config={k: v for k, v in hit_col_config.items() if k in hit_cols},
        )

        # ---- Marker selection ----
        marker_supported = marker_rules()
        today_hit_with_marker = [name for name, r in results.items()
                                 if r.hit and name in marker_supported]
        marker_options = [r for r in marker_supported]

        # 每檔股票獨立的 multiselect key — 切股自動拿該股的初始預設（命中規則）
        # 用戶在同一檔內的手動加減會記住；切到別檔不互相影響
        marker_key = f"marker_select__{selected.replace('.', '_')}"

        chosen_markers = st.multiselect(
            "🎯 在圖上標記訊號（依當前個股命中狀態自動勾選）",
            options=marker_options,
            default=today_hit_with_marker,
            format_func=lambda r: f"{rule_zh(r)}（{rule_summary(r)}）",
            help="預設勾選此股今日命中的規則；可手動加減；同一檔內變更會記住。",
            key=marker_key,
        )


        # ---------- Lightweight Charts v5 multi-pane ----------
        import json as _json

        # Indicators
        ma5_series = sma(df["close"], ind_p["ma"]["short"])
        ma20_series = sma(df["close"], ind_p["ma"]["mid"])
        b = bbands(df["close"], ind_p["bbands"]["period"], ind_p["bbands"]["std"])
        kd = kd_taiwan(df["high"], df["low"], df["close"], ind_p["kd"]["k_period"])
        m = macd(df["close"], ind_p["macd"]["fast"], ind_p["macd"]["slow"],
                 ind_p["macd"]["signal"])
        vol_ma5 = df["volume"].rolling(5, min_periods=5).mean()

        def _t(d):
            return d.strftime("%Y-%m-%d")

        candle_data = [
            {"time": _t(idx), "open": float(r.open), "high": float(r.high),
             "low": float(r.low), "close": float(r.close)}
            for idx, r in df.iterrows()
        ]
        ma5_data = [{"time": _t(d), "value": float(v)} for d, v in ma5_series.dropna().items()]
        ma20_data = [{"time": _t(d), "value": float(v)} for d, v in ma20_series.dropna().items()]
        bb_upper_data = [{"time": _t(d), "value": float(v)} for d, v in b["upper"].dropna().items()]
        bb_lower_data = [{"time": _t(d), "value": float(v)} for d, v in b["lower"].dropna().items()]
        vol_data = [
            {"time": _t(idx), "value": float(r.volume),
             "color": "rgba(244,168,168,0.7)" if r.close >= r.open
             else "rgba(168,212,185,0.7)"}
            for idx, r in df.iterrows()
        ]
        vol_ma5_data = [{"time": _t(d), "value": float(v)} for d, v in vol_ma5.dropna().items()]
        k_data = [{"time": _t(d), "value": float(v)} for d, v in kd["k"].dropna().items()]
        d_data = [{"time": _t(d), "value": float(v)} for d, v in kd["d"].dropna().items()]
        macd_dif_data = [{"time": _t(d), "value": float(v)} for d, v in m["macd"].dropna().items()]
        macd_sig_data = [{"time": _t(d), "value": float(v)} for d, v in m["signal"].dropna().items()]
        macd_hist_data = [
            {"time": _t(d), "value": float(v),
             "color": "#d62728" if v >= 0 else "#26a65b"}
            for d, v in m["hist"].dropna().items()
        ]

        # ---------- Marker config (LWC has 4 shapes: arrowUp/arrowDown/circle/square) ----------
        MARKER_LWC = {
            # 趨勢類
            "ma_golden_cross":         dict(pane=0, shape="arrowUp", pos="belowBar", color="#ff8c00", text="金叉"),
            "ma_bullish_alignment":    dict(pane=0, shape="arrowUp", pos="belowBar", color="#2e7d32", text="排列"),
            "ma_converge_breakout":    dict(pane=0, shape="arrowUp", pos="aboveBar", color="#fbc02d", text="糾結突破"),
            "pullback_holds_ma20":     dict(pane=0, shape="circle",  pos="inBar",    color="#1565c0", text="守月線"),
            "macd_hist_turn_positive": dict(pane=3, shape="arrowUp", pos="belowBar", color="#d32f2f", text="MACD翻紅"),
            "adx_strong_uptrend":      dict(pane=0, shape="circle",  pos="belowBar", color="#1b5e20", text="ADX強"),
            # 動能類
            "kd_oversold_golden":      dict(pane=2, shape="arrowUp", pos="belowBar", color="#26a65b", text="KD金叉"),
            "rsi_recover":             dict(pane=2, shape="circle",  pos="inBar",    color="#66bb6a", text="RSI"),
            # 量價類
            "volume_breakout":         dict(pane=1, shape="arrowUp", pos="aboveBar", color="#ffb300", text="爆量"),
            "price_volume_surge":      dict(pane=1, shape="arrowUp", pos="aboveBar", color="#ffd54f", text="量價揚"),
            "obv_new_high":            dict(pane=0, shape="square",  pos="belowBar", color="#8d6e63", text="OBV高"),
            "volume_dry_red_surge":    dict(pane=1, shape="arrowUp", pos="aboveBar", color="#ef6c00", text="縮量轉攻"),
            # 波動類
            "bbands_lower_bounce":     dict(pane=0, shape="arrowUp", pos="belowBar", color="#00acc1", text="下軌彈"),
            "bbands_upper_break":      dict(pane=0, shape="circle",  pos="aboveBar", color="#9c27b0", text="突破上軌"),
            "atr_expansion":           dict(pane=0, shape="square",  pos="aboveBar", color="#757575", text="ATR↑"),
            # 型態類
            "long_red_breakout":       dict(pane=0, shape="arrowUp", pos="aboveBar", color="#c62828", text="長紅"),
            "long_lower_shadow":       dict(pane=0, shape="arrowUp", pos="belowBar", color="#1565c0", text="止跌"),
            "doji_or_spinning_top":    dict(pane=0, shape="circle",  pos="inBar",    color="#6a1b9a", text="變盤"),
            "double_bottom":           dict(pane=0, shape="arrowUp", pos="belowBar", color="#e91e63", text="W底"),
            # ===== 空頭/出場訊號（arrowDown + 冷色系）=====
            # 趨勢類 反向
            "ma_death_cross":          dict(pane=0, shape="arrowDown", pos="aboveBar", color="#5e35b1", text="死叉"),
            "ma_bearish_alignment":    dict(pane=0, shape="arrowDown", pos="aboveBar", color="#3949ab", text="空排"),
            "ma_converge_breakdown":   dict(pane=0, shape="arrowDown", pos="aboveBar", color="#283593", text="糾結跌破"),
            "rebound_caps_ma20":       dict(pane=0, shape="circle",   pos="inBar",    color="#455a64", text="月線壓"),
            "macd_hist_turn_negative": dict(pane=3, shape="arrowDown", pos="aboveBar", color="#37474f", text="MACD翻綠"),
            "adx_strong_downtrend":    dict(pane=0, shape="circle",   pos="aboveBar", color="#37474f", text="ADX空"),
            # 動能類 反向
            "kd_overbought_dead":      dict(pane=2, shape="arrowDown", pos="aboveBar", color="#4527a0", text="KD死叉"),
            "rsi_overbought_drop":     dict(pane=2, shape="circle",   pos="inBar",    color="#546e7a", text="RSI落"),
            # 量價類 反向
            "volume_breakdown":        dict(pane=1, shape="arrowDown", pos="aboveBar", color="#00695c", text="爆量殺"),
            "price_volume_collapse":   dict(pane=1, shape="arrowDown", pos="aboveBar", color="#37474f", text="量增跌"),
            "obv_new_low":             dict(pane=0, shape="square",   pos="aboveBar", color="#1a237e", text="OBV低"),
            "volume_dry_black_surge":  dict(pane=1, shape="arrowDown", pos="aboveBar", color="#263238", text="縮量起跌"),
            # 波動類 反向
            "bbands_upper_reject":     dict(pane=0, shape="arrowDown", pos="aboveBar", color="#1a237e", text="上軌壓"),
            "bbands_lower_break":      dict(pane=0, shape="arrowDown", pos="belowBar", color="#616161", text="跌破下軌"),
            # 型態類 反向
            "long_black_breakdown":    dict(pane=0, shape="arrowDown", pos="aboveBar", color="#283593", text="長黑"),
            "long_upper_shadow":       dict(pane=0, shape="arrowDown", pos="aboveBar", color="#00695c", text="止漲"),
            "double_top":              dict(pane=0, shape="arrowDown", pos="aboveBar", color="#3e2723", text="M頭"),
        }
        SHAPE_SYM = {"arrowUp": "↑", "arrowDown": "↓", "circle": "●", "square": "■"}

        markers_by_pane = {0: [], 1: [], 2: [], 3: []}
        for rule_id in chosen_markers:
            cfg_m = MARKER_LWC.get(rule_id)
            if not cfg_m:
                continue
            occs = find_markers(rule_id, df, cfg_static["indicators"])
            for occ in occs:
                d = occ.get("second_date") or occ.get("date")
                if d is None:
                    continue
                markers_by_pane[cfg_m["pane"]].append({
                    "time": _t(d),
                    "position": cfg_m["pos"],
                    "color": cfg_m["color"],
                    "shape": cfg_m["shape"],
                    # 不放 text — 由下方標記對照表辨識，避免圖上太花
                })
        for k_p in markers_by_pane:
            markers_by_pane[k_p].sort(key=lambda x: x["time"])

        # ---------- 動態 legend ----------
        legend_items = []
        for rule_id in chosen_markers:
            cfg_m = MARKER_LWC.get(rule_id)
            if not cfg_m:
                continue
            sym = SHAPE_SYM.get(cfg_m["shape"], "●")
            legend_items.append(
                f"<span style='display:inline-block;margin-right:1rem;white-space:nowrap;'>"
                f"<b style='color:{cfg_m['color']};'>{sym} {cfg_m['text']}</b>"
                f"<span style='color:#888;font-size:0.85em;'> {rule_zh(rule_id)}</span></span>"
            )
        legend_html_inner = "".join(legend_items) if legend_items else \
            "<span style='color:#888'>未選擇任何標記</span>"
        st.markdown(
            f"<div style='display:flex;align-items:center;gap:0.4rem;flex-wrap:wrap;"
            f"padding:0.5rem 0.8rem;background:#f8f9fa;border:1px solid #e0e0e0;"
            f"border-radius:6px;margin-bottom:0.4rem;font-size:0.95rem;'>"
            f"<span style='font-weight:600;color:#555;'>🎯 標記對照</span>"
            f"{legend_html_inner}</div>",
            unsafe_allow_html=True,
        )

        # ---------- Build payload + HTML ----------
        payload = {
            "candle": candle_data,
            "ma5": ma5_data, "ma20": ma20_data,
            "bb_upper": bb_upper_data, "bb_lower": bb_lower_data,
            "vol": vol_data, "vol_ma5": vol_ma5_data,
            "k": k_data, "d": d_data,
            "macd_dif": macd_dif_data, "macd_sig": macd_sig_data,
            "macd_hist": macd_hist_data,
            "markers_p0": markers_by_pane[0],
            "markers_p1": markers_by_pane[1],
            "markers_p2": markers_by_pane[2],
            "markers_p3": markers_by_pane[3],
        }
        payload_json = _json.dumps(payload)
        ma_short = ind_p["ma"]["short"]
        ma_mid = ind_p["ma"]["mid"]

        chart_html_template = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  html, body { margin: 0; padding: 0; font-family: -apple-system, "Microsoft JhengHei", sans-serif; }
  #chart { width: 100%; height: 800px; position: relative; }
  .legend {
    position: absolute; left: 12px; z-index: 10;
    font-size: 11px; background: rgba(255,255,255,0.92);
    border: 1px solid #ddd; border-radius: 3px; padding: 3px 8px;
    line-height: 1.6; pointer-events: none;
  }
  .legend .item { display: inline-block; margin-right: 10px; }
  .legend .swatch {
    display: inline-block; width: 12px; height: 2px; vertical-align: middle;
    margin-right: 4px;
  }
</style>
<script src="https://unpkg.com/lightweight-charts@5.0.7/dist/lightweight-charts.standalone.production.js"></script>
</head>
<body>
<div id="chart"></div>
<div class="legend" id="legend-k" style="top: 6px;"></div>
<div class="legend" id="legend-vol" style="top: 432px;"></div>
<div class="legend" id="legend-kd" style="top: 548px;"></div>
<div class="legend" id="legend-macd" style="top: 690px;"></div>

<script>
window.addEventListener('error', function(e) {
  var d = document.createElement('div');
  d.style.cssText = 'position:fixed;top:0;left:0;right:0;background:#fee;color:#c00;padding:8px;font-size:11px;z-index:9999;border:1px solid #c00';
  d.innerText = 'JS Error: ' + e.message + ' at ' + (e.filename || '?') + ':' + (e.lineno || '?');
  document.body.appendChild(d);
});

const D = __PAYLOAD__;
const MA_SHORT = __MA_SHORT__;
const MA_MID = __MA_MID__;

if (typeof LightweightCharts === 'undefined') {
  document.body.innerHTML = '<div style="padding:20px;color:red;font-size:14px">❌ LightweightCharts CDN failed to load. Check network/sandbox.</div>';
  throw new Error('LightweightCharts not loaded');
}
const LWC = LightweightCharts;

// 等 iframe 父容器有實際寬度才建 chart（否則 canvas 畫在 0 寬不會顯示）
function _waitWidth(cb, attempts) {
  attempts = attempts || 0;
  var div = document.getElementById('chart');
  if (div && div.clientWidth > 100) { cb(); return; }
  if (attempts > 100) { cb(); return; }  // give up after 5s, render anyway
  setTimeout(function(){ _waitWidth(cb, attempts + 1); }, 50);
}

_waitWidth(function() { runChart(); });

function runChart() {

const chart = LWC.createChart(document.getElementById('chart'), {
  layout: {
    background: { type: 'solid', color: 'white' },
    textColor: '#222', fontSize: 12,
    panes: { separatorColor: '#cfcfcf', separatorHoverColor: 'rgba(0,0,0,0.1)' },
  },
  grid: { vertLines: { color: '#eef0f3' }, horzLines: { color: '#eef0f3' } },
  crosshair: {
    mode: 0,
    vertLine: { width: 1, color: '#1f3a5f', style: 0,
                labelBackgroundColor: '#1f3a5f' },
    horzLine: { width: 1, color: '#aaa', style: 1,
                labelBackgroundColor: '#1f3a5f' },
  },
  rightPriceScale: { borderColor: '#ccc' },
  timeScale: { borderColor: '#ccc' },
});

const candleSeries = chart.addSeries(LWC.CandlestickSeries, {
  upColor: '#d62728', downColor: '#26a65b',
  wickUpColor: '#d62728', wickDownColor: '#26a65b',
  borderVisible: false, priceLineVisible: false, lastValueVisible: true,
});
candleSeries.setData(D.candle);
const ma5Series = chart.addSeries(LWC.LineSeries, {
  color: '#ff8c00', lineWidth: 1.5, priceLineVisible: false, lastValueVisible: false,
});
ma5Series.setData(D.ma5);
const ma20Series = chart.addSeries(LWC.LineSeries, {
  color: '#2962ff', lineWidth: 1.5, priceLineVisible: false, lastValueVisible: false,
});
ma20Series.setData(D.ma20);
const bbU = chart.addSeries(LWC.LineSeries, {
  color: '#9aa0a6', lineWidth: 1, lineStyle: 1,
  priceLineVisible: false, lastValueVisible: false,
});
bbU.setData(D.bb_upper);
const bbL = chart.addSeries(LWC.LineSeries, {
  color: '#9aa0a6', lineWidth: 1, lineStyle: 1,
  priceLineVisible: false, lastValueVisible: false,
});
bbL.setData(D.bb_lower);
if (D.markers_p0.length) LWC.createSeriesMarkers(candleSeries, D.markers_p0);

const volSeries = chart.addSeries(LWC.HistogramSeries, {
  priceFormat: { type: 'volume' },
}, 1);
volSeries.setData(D.vol);
const volMaSeries = chart.addSeries(LWC.LineSeries, {
  color: '#555', lineWidth: 1, lineStyle: 2,
  priceLineVisible: false, lastValueVisible: false,
}, 1);
volMaSeries.setData(D.vol_ma5);
if (D.markers_p1.length) LWC.createSeriesMarkers(volSeries, D.markers_p1);

const kSeries = chart.addSeries(LWC.LineSeries, {
  color: '#d62728', lineWidth: 1.5, priceLineVisible: false, lastValueVisible: true,
}, 2);
kSeries.setData(D.k);
const dSeries = chart.addSeries(LWC.LineSeries, {
  color: '#2962ff', lineWidth: 1.5, priceLineVisible: false, lastValueVisible: true,
}, 2);
dSeries.setData(D.d);
if (D.markers_p2.length) LWC.createSeriesMarkers(kSeries, D.markers_p2);

const histSeries = chart.addSeries(LWC.HistogramSeries, {
  priceFormat: { type: 'price', precision: 3, minMove: 0.001 },
}, 3);
histSeries.setData(D.macd_hist);
const difSeries = chart.addSeries(LWC.LineSeries, {
  color: '#2962ff', lineWidth: 1.5, priceLineVisible: false, lastValueVisible: false,
}, 3);
difSeries.setData(D.macd_dif);
const sigSeries = chart.addSeries(LWC.LineSeries, {
  color: '#ff8c00', lineWidth: 1.5, priceLineVisible: false, lastValueVisible: false,
}, 3);
sigSeries.setData(D.macd_sig);
if (D.markers_p3.length) LWC.createSeriesMarkers(histSeries, D.markers_p3);

function setPaneHeights() {
  try {
    const panes = chart.panes();
    if (panes.length >= 4) {
      panes[0].setHeight(420);
      panes[1].setHeight(110);
      panes[2].setHeight(140);
      panes[3].setHeight(140);
    }
  } catch(e) {}
}
setTimeout(setPaneHeights, 100);

function find(arr, time) { return arr.find(x => x.time === time); }
function staticK() {
  return `<span class="item"><span class="swatch" style="background:#ff8c00"></span>MA${MA_SHORT}</span>` +
         `<span class="item"><span class="swatch" style="background:#2962ff"></span>MA${MA_MID}</span>` +
         `<span class="item" style="color:#9aa0a6">布林通道</span>`;
}
function staticKD() {
  return `<span class="item"><span class="swatch" style="background:#d62728"></span>K</span>` +
         `<span class="item"><span class="swatch" style="background:#2962ff"></span>D</span>`;
}
function staticMACD() {
  return `<span class="item"><span class="swatch" style="background:#2962ff"></span>DIF</span>` +
         `<span class="item"><span class="swatch" style="background:#ff8c00"></span>MACD</span>`;
}
document.getElementById('legend-k').innerHTML = staticK();
document.getElementById('legend-vol').innerHTML = '成交量';
document.getElementById('legend-kd').innerHTML = staticKD();
document.getElementById('legend-macd').innerHTML = staticMACD();

chart.subscribeCrosshairMove(p => {
  const time = p && p.time ? p.time : null;
  if (!time) {
    document.getElementById('legend-k').innerHTML = staticK();
    document.getElementById('legend-vol').innerHTML = '成交量';
    document.getElementById('legend-kd').innerHTML = staticKD();
    document.getElementById('legend-macd').innerHTML = staticMACD();
    return;
  }
  const c = find(D.candle, time);
  const m5 = find(D.ma5, time);
  const m20 = find(D.ma20, time);
  let h = '';
  if (c) h += `<span class="item"><b>${time}</b> 開${c.open} 高${c.high} 低${c.low} <b style="color:${c.close >= c.open ? '#d62728' : '#26a65b'}">收${c.close}</b></span>`;
  if (m5) h += `<span class="item"><span class="swatch" style="background:#ff8c00"></span>MA${MA_SHORT} ${m5.value.toFixed(2)}</span>`;
  if (m20) h += `<span class="item"><span class="swatch" style="background:#2962ff"></span>MA${MA_MID} ${m20.value.toFixed(2)}</span>`;
  document.getElementById('legend-k').innerHTML = h;
  const v = find(D.vol, time);
  document.getElementById('legend-vol').innerHTML = v ? `量 ${Math.round(v.value).toLocaleString()}` : '成交量';
  const kv = find(D.k, time);
  const dv = find(D.d, time);
  let kdh = '';
  if (kv) kdh += `<span class="item"><span class="swatch" style="background:#d62728"></span>K ${kv.value.toFixed(1)}</span>`;
  if (dv) kdh += `<span class="item"><span class="swatch" style="background:#2962ff"></span>D ${dv.value.toFixed(1)}</span>`;
  document.getElementById('legend-kd').innerHTML = kdh || staticKD();
  const dif = find(D.macd_dif, time);
  const sig = find(D.macd_sig, time);
  const mh = find(D.macd_hist, time);
  let mhtml = '';
  if (mh) mhtml += `<span class="item">柱 <b style="color:${mh.value >= 0 ? '#d62728' : '#26a65b'}">${mh.value.toFixed(3)}</b></span>`;
  if (dif) mhtml += `<span class="item"><span class="swatch" style="background:#2962ff"></span>DIF ${dif.value.toFixed(3)}</span>`;
  if (sig) mhtml += `<span class="item"><span class="swatch" style="background:#ff8c00"></span>MACD ${sig.value.toFixed(3)}</span>`;
  document.getElementById('legend-macd').innerHTML = mhtml || staticMACD();
});

window.addEventListener('resize', () => {
  chart.applyOptions({ width: document.getElementById('chart').clientWidth });
});
chart.timeScale().fitContent();

}  // end runChart
</script>
</body>
</html>
"""
        chart_html = chart_html_template.replace("__PAYLOAD__", payload_json)
        chart_html = chart_html.replace("__MA_SHORT__", str(ma_short))
        chart_html = chart_html.replace("__MA_MID__", str(ma_mid))

        components.html(chart_html, height=820, scrolling=False)
