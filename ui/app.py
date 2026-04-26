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
import plotly.graph_objects as go
from plotly.subplots import make_subplots

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
    """Read persistent state from browser localStorage into session_state (once per session)."""
    if st.session_state.get("_ls_loaded"):
        return
    raw_wl = _LS.getItem(WATCHLIST_KEY)
    try:
        st.session_state.watchlist = json.loads(raw_wl) if raw_wl else []
    except Exception:
        st.session_state.watchlist = []
    if "custom_text" not in st.session_state:
        st.session_state.custom_text = _LS.getItem(CUSTOM_TEXT_KEY) or ""
    st.session_state._ls_loaded = True


def save_watchlist():
    _LS.setItem(WATCHLIST_KEY, json.dumps(st.session_state.watchlist))


def save_custom_text():
    _LS.setItem(CUSTOM_TEXT_KEY, st.session_state.get("custom_text", ""))

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
  padding-bottom: 2.5rem;
  max-width: 1400px;
}
html, body, [class*="st-"] { font-size: 16px; }
h1 { margin-bottom: 0.6rem; font-size: 1.9rem; }
h2 { font-size: 1.4rem; margin-top: 1rem; }
h3 { font-size: 1.15rem; margin-top: 0.8rem; }
.stDataFrame { font-size: 0.95rem; }
.stDataFrame th, .stDataFrame td { padding: 0.5rem 0.7rem !important; }
.stTabs [data-baseweb="tab"] {
  padding: 0.7rem 1.2rem;
  font-size: 1.05rem;
}
.stMarkdown p { line-height: 1.6; }
[data-testid="stSidebar"] [data-testid="stMarkdown"] { font-size: 0.95rem; }
.stCheckbox label { font-size: 0.95rem; }
[data-testid="stDataFrameResizable"] { font-size: 0.95rem; }

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
        chosen_markers = st.multiselect(
            "🎯 在圖上標記訊號",
            options=marker_options,
            default=today_hit_with_marker,
            format_func=lambda r: f"{rule_zh(r)}（{rule_summary(r)}）",
            help="標記過去 60 天所有觸發點。預設勾選今日命中的規則。",
            key="marker_select",
        )

        # ---------- Color palette ----------
        CL = {
            "k_up": "#d62728",      # 台股紅
            "k_down": "#26a65b",    # 台股綠
            "ma5": "#ff8c00",       # 橘
            "ma20": "#2962ff",      # 藍
            "bb_band": "#9aa0a6",   # 灰（虛線）
            "vol_up": "#f4a8a8",    # 淡紅
            "vol_down": "#a8d4b9",  # 淡綠
            "vol_ma5": "#555555",
            "kd_k": "#d62728",
            "kd_d": "#2962ff",
            "kd_oversold": "#aaaaaa",
            "macd_dif": "#2962ff",
            "macd_sig": "#ff8c00",
            "macd_up": "#d62728",
            "macd_down": "#26a65b",
            "grid": "#eef0f3",
        }

        fig = make_subplots(
            rows=4, cols=1, shared_xaxes=True,
            row_heights=[0.50, 0.16, 0.17, 0.17],
            vertical_spacing=0.03,
            subplot_titles=("K 線 + 均線 + 布林通道", "成交量",
                            "KD（台股 9-3-3）", "MACD"),
        )

        # ---- Row 1: 布林（最底）、均線、K 線（最上）----
        b = bbands(df["close"], ind_p["bbands"]["period"], ind_p["bbands"]["std"])
        fig.add_trace(go.Scatter(x=df.index, y=b["upper"], name="布林上軌",
                                 line=dict(dash="dot", width=1, color=CL["bb_band"]),
                                 hovertemplate="布林上軌 %{y:.2f}<extra></extra>"),
                      row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=b["lower"], name="布林下軌",
                                 line=dict(dash="dot", width=1, color=CL["bb_band"]),
                                 fill="tonexty", fillcolor="rgba(154,160,166,0.06)",
                                 hovertemplate="布林下軌 %{y:.2f}<extra></extra>"),
                      row=1, col=1)
        ma5_series = sma(df["close"], ind_p["ma"]["short"])
        ma20_series = sma(df["close"], ind_p["ma"]["mid"])
        fig.add_trace(go.Scatter(x=df.index, y=ma5_series,
                                 name=f"MA{ind_p['ma']['short']}",
                                 line=dict(width=1.4, color=CL["ma5"]),
                                 hovertemplate=f"MA{ind_p['ma']['short']} %{{y:.2f}}<extra></extra>"),
                      row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=ma20_series,
                                 name=f"MA{ind_p['ma']['mid']}",
                                 line=dict(width=1.4, color=CL["ma20"]),
                                 hovertemplate=f"MA{ind_p['ma']['mid']} %{{y:.2f}}<extra></extra>"),
                      row=1, col=1)
        fig.add_trace(go.Candlestick(x=df.index, open=df["open"], high=df["high"],
                                     low=df["low"], close=df["close"], name="K 線",
                                     increasing_line_color=CL["k_up"],
                                     increasing_fillcolor=CL["k_up"],
                                     decreasing_line_color=CL["k_down"],
                                     decreasing_fillcolor=CL["k_down"],
                                     line=dict(width=1)),
                      row=1, col=1)

        # ---- Row 2: Volume ----
        vol_colors = [CL["vol_up"] if c >= o else CL["vol_down"]
                      for c, o in zip(df["close"], df["open"])]
        fig.add_trace(go.Bar(x=df.index, y=df["volume"], name="成交量",
                             marker_color=vol_colors,
                             marker_line_width=0,
                             hovertemplate="成交量 %{y:,.0f}<extra></extra>"),
                      row=2, col=1)
        vol_ma5 = df["volume"].rolling(5, min_periods=5).mean()
        fig.add_trace(go.Scatter(x=df.index, y=vol_ma5, name="量 MA5",
                                 line=dict(width=1, color=CL["vol_ma5"], dash="dash"),
                                 hovertemplate="量 MA5 %{y:,.0f}<extra></extra>"),
                      row=2, col=1)

        # ---- Row 3: KD ----
        kd = kd_taiwan(df["high"], df["low"], df["close"], ind_p["kd"]["k_period"])
        fig.add_trace(go.Scatter(x=df.index, y=kd["k"], name="K 值",
                                 line=dict(width=1.5, color=CL["kd_k"]),
                                 hovertemplate="K %{y:.1f}<extra></extra>"),
                      row=3, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=kd["d"], name="D 值",
                                 line=dict(width=1.5, color=CL["kd_d"]),
                                 hovertemplate="D %{y:.1f}<extra></extra>"),
                      row=3, col=1)
        fig.add_hline(y=ind_p["kd"]["oversold"], line_dash="dash",
                      line_color=CL["kd_oversold"], line_width=1, row=3, col=1)
        fig.add_hline(y=80, line_dash="dash",
                      line_color=CL["kd_oversold"], line_width=1, row=3, col=1)

        # ---- Row 4: MACD ----
        m = macd(df["close"], ind_p["macd"]["fast"], ind_p["macd"]["slow"],
                 ind_p["macd"]["signal"])
        hist_colors = [CL["macd_up"] if h >= 0 else CL["macd_down"]
                       for h in m["hist"].fillna(0)]
        fig.add_trace(go.Bar(x=df.index, y=m["hist"], name="MACD 柱",
                             marker_color=hist_colors, marker_line_width=0,
                             hovertemplate="柱 %{y:.3f}<extra></extra>"),
                      row=4, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=m["macd"], name="DIF",
                                 line=dict(width=1.4, color=CL["macd_dif"]),
                                 hovertemplate="DIF %{y:.3f}<extra></extra>"),
                      row=4, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=m["signal"], name="MACD",
                                 line=dict(width=1.4, color=CL["macd_sig"]),
                                 hovertemplate="MACD %{y:.3f}<extra></extra>"),
                      row=4, col=1)

        # ---- Rule markers ----
        marker_params = cfg_static["indicators"]
        marker_params["volume"] = cfg_static["indicators"]["volume"]  # ensure key
        marker_params["kd"] = cfg_static["indicators"]["kd"]
        marker_params["ma"] = cfg_static["indicators"]["ma"]

        for rule_id in chosen_markers:
            occurrences = find_markers(rule_id, df, marker_params)
            if not occurrences:
                continue
            label = rule_zh(rule_id)

            if rule_id == "ma_golden_cross":
                # 紅 K 圖下方畫 ↑ 三角
                xs = [o["date"] for o in occurrences]
                ys = [o["price"] * 0.985 for o in occurrences]  # 略低於最低
                fig.add_trace(go.Scatter(
                    x=xs, y=ys, name=f"⭐ {label}",
                    mode="markers+text",
                    marker=dict(symbol="triangle-up", size=14,
                                color="#ff8c00",
                                line=dict(width=1.5, color="#cc7000")),
                    text=["金叉"] * len(xs),
                    textposition="bottom center",
                    textfont=dict(size=10, color="#cc7000"),
                    hovertemplate=f"{label}<br>%{{x|%Y-%m-%d}}<extra></extra>",
                ), row=1, col=1)

            elif rule_id == "volume_breakout":
                # 量子圖那根改色（畫 marker 在量上方）
                xs = [o["date"] for o in occurrences]
                ys = [o["volume"] * 1.05 for o in occurrences]
                fig.add_trace(go.Scatter(
                    x=xs, y=ys, name=f"⭐ {label}",
                    mode="markers",
                    marker=dict(symbol="star", size=12,
                                color="#ffb300",
                                line=dict(width=1.2, color="#cc7a00")),
                    hovertemplate=(f"{label}<br>%{{x|%Y-%m-%d}}<br>"
                                   "量 %{customdata:.1f}× 5MA<extra></extra>"),
                    customdata=[o["ratio"] for o in occurrences],
                ), row=2, col=1)

            elif rule_id == "kd_oversold_golden":
                # KD 子圖加綠色三角
                xs = [o["date"] for o in occurrences]
                ys = [o["k"] for o in occurrences]
                fig.add_trace(go.Scatter(
                    x=xs, y=ys, name=f"⭐ {label}",
                    mode="markers",
                    marker=dict(symbol="triangle-up", size=12,
                                color="#26a65b",
                                line=dict(width=1.2, color="#1e7d44")),
                    hovertemplate=f"{label}<br>%{{x|%Y-%m-%d}}<br>K=%{{y:.1f}}<extra></extra>",
                ), row=3, col=1)

            elif rule_id == "bbands_upper_break":
                # K 線那根上方畫 ★
                xs = [o["date"] for o in occurrences]
                ys = [o["price"] * 1.012 for o in occurrences]  # 略高於 high
                fig.add_trace(go.Scatter(
                    x=xs, y=ys, name=f"⭐ {label}",
                    mode="markers",
                    marker=dict(symbol="star", size=13,
                                color="#9c27b0",
                                line=dict(width=1.2, color="#6a1b9a")),
                    hovertemplate=f"{label}<br>%{{x|%Y-%m-%d}}<extra></extra>",
                ), row=1, col=1)

            elif rule_id == "long_lower_shadow":
                # K 線下方畫 ⤴ 朝上箭頭
                xs = [o["date"] for o in occurrences]
                ys = [o["price"] * 0.985 for o in occurrences]
                fig.add_trace(go.Scatter(
                    x=xs, y=ys, name=f"⭐ {label}",
                    mode="markers+text",
                    marker=dict(symbol="arrow-up", size=14,
                                color="#1565c0",
                                line=dict(width=1.2, color="#0d3d8a")),
                    text=["止跌"] * len(xs),
                    textposition="bottom center",
                    textfont=dict(size=10, color="#1565c0"),
                    hovertemplate=f"{label}<br>%{{x|%Y-%m-%d}}<extra></extra>",
                ), row=1, col=1)

            elif rule_id == "double_bottom":
                # 兩個低點畫圓圈，並用虛線連起
                for occ in occurrences:
                    fig.add_trace(go.Scatter(
                        x=[occ["first_date"], occ["second_date"]],
                        y=[occ["first_price"] * 0.99, occ["second_price"] * 0.99],
                        name=f"⭐ {label}",
                        mode="lines+markers+text",
                        marker=dict(symbol="circle", size=14,
                                    color="rgba(255,255,255,0)",
                                    line=dict(width=2, color="#e91e63")),
                        line=dict(width=1.5, color="#e91e63", dash="dash"),
                        text=["第一腳", "第二腳"],
                        textposition="bottom center",
                        textfont=dict(size=10, color="#e91e63"),
                        hovertemplate=f"{label}<extra></extra>",
                        showlegend=True,
                    ), row=1, col=1)

        # ---- Layout ----
        fig.update_layout(
            height=720,
            xaxis_rangeslider_visible=False,
            showlegend=True,
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.04,
                        xanchor="right", x=1, font=dict(size=11),
                        bgcolor="rgba(255,255,255,0.7)"),
            margin=dict(l=10, r=10, t=50, b=10),
            plot_bgcolor="white",
            paper_bgcolor="white",
            font=dict(size=11),
        )
        # Smaller subplot titles
        for ann in fig["layout"]["annotations"]:
            ann["font"] = dict(size=12, color="#333")
            ann["x"] = 0.0
            ann["xanchor"] = "left"
        # Grid styling
        fig.update_xaxes(showgrid=True, gridcolor=CL["grid"], gridwidth=1,
                         showspikes=True, spikecolor="#aaa",
                         spikethickness=1, spikedash="dot", spikemode="across")
        fig.update_yaxes(showgrid=True, gridcolor=CL["grid"], gridwidth=1)
        # Hide weekend gaps for daily K
        fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])

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
