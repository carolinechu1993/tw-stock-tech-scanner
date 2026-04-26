"""TradingView Lightweight Charts v5 prototype — single chart, multi-pane native API.

Run: streamlit run prototype/lwc_demo.py --server.port 8503
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import json
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from src.data.yfinance_src import YFinanceSource
from src.data.cache import ParquetCache
from src.indicators.trend import sma, macd
from src.indicators.momentum import kd_taiwan
from src.signals.markers import find_markers
from src.scanner import load_config

st.set_page_config(page_title="LWC v5 Multi-Pane Prototype", layout="wide")
st.title("🧪 Lightweight Charts v5 Prototype（單 chart 多 pane 原生）")
st.caption("用 v5 native pane API：所有對齊與貫穿線都是內建行為")

cfg = load_config(ROOT / "config.yaml")
cache = ParquetCache(cfg["data"]["cache_dir"], ttl_minutes=60)
src = YFinanceSource(cache=cache)

DEMO_STOCKS = {
    "2330.TW 台積電": "2330.TW",
    "2454.TW 聯發科": "2454.TW",
    "2317.TW 鴻海": "2317.TW",
    "2603.TW 長榮": "2603.TW",
    "3008.TW 大立光": "3008.TW",
}

picked = st.selectbox("股票", list(DEMO_STOCKS.keys()))
symbol = DEMO_STOCKS[picked]

# 標記對照表（prototype 示意 2 條規則；正式版會列全部勾選的）
st.markdown(
    """
<div style='display:flex; gap:1.5rem; padding:0.5rem 0.8rem; background:#f8f9fa;
            border:1px solid #e0e0e0; border-radius:6px; margin-bottom:0.4rem;
            font-size:0.9rem;'>
  <span style='font-weight:600; color:#555;'>🎯 標記對照</span>
  <span><b style='color:#ff8c00;'>↑ 金叉</b> = 均線黃金交叉</span>
  <span><b style='color:#9c27b0;'>● 突破</b> = 突破布林上軌</span>
  <span style='color:#888;'>（正式版會跟著當前個股命中規則動態列出）</span>
</div>
    """,
    unsafe_allow_html=True,
)

with st.spinner(f"載入 {symbol}..."):
    df = src.get_history(symbol, days=120)
    df.index = pd.to_datetime(df.index)


def _t(d):
    return d.strftime("%Y-%m-%d")


# 資料準備
candle_data = [
    {"time": _t(idx), "open": float(r.open), "high": float(r.high),
     "low": float(r.low), "close": float(r.close)}
    for idx, r in df.iterrows()
]

ma5 = sma(df["close"], 5)
ma20 = sma(df["close"], 20)
ma5_data = [{"time": _t(d), "value": float(v)} for d, v in ma5.dropna().items()]
ma20_data = [{"time": _t(d), "value": float(v)} for d, v in ma20.dropna().items()]

vol_data = [
    {"time": _t(idx), "value": float(r.volume),
     "color": "rgba(244,168,168,0.7)" if r.close >= r.open
     else "rgba(168,212,185,0.7)"}
    for idx, r in df.iterrows()
]

kd = kd_taiwan(df["high"], df["low"], df["close"], 9)
k_data = [{"time": _t(d), "value": float(v)} for d, v in kd["k"].dropna().items()]
d_data = [{"time": _t(d), "value": float(v)} for d, v in kd["d"].dropna().items()]

m = macd(df["close"], 12, 26, 9)
macd_dif = [{"time": _t(d), "value": float(v)} for d, v in m["macd"].dropna().items()]
macd_sig = [{"time": _t(d), "value": float(v)} for d, v in m["signal"].dropna().items()]
macd_hist = [
    {"time": _t(d), "value": float(v),
     "color": "#d62728" if v >= 0 else "#26a65b"}
    for d, v in m["hist"].dropna().items()
]

gc_marks = find_markers("ma_golden_cross", df, cfg["indicators"])
break_marks = find_markers("bbands_upper_break", df, cfg["indicators"])
candle_markers = []
for occ in gc_marks:
    candle_markers.append({
        "time": _t(occ["date"]), "position": "belowBar",
        "color": "#ff8c00", "shape": "arrowUp", "text": "金叉",
    })
for occ in break_marks:
    candle_markers.append({
        "time": _t(occ["date"]), "position": "aboveBar",
        "color": "#9c27b0", "shape": "circle", "text": "突破",
    })
candle_markers.sort(key=lambda x: x["time"])

payload_json = json.dumps({
    "candle": candle_data, "ma5": ma5_data, "ma20": ma20_data,
    "vol": vol_data, "k": k_data, "d": d_data,
    "macd_dif": macd_dif, "macd_sig": macd_sig, "macd_hist": macd_hist,
    "markers": candle_markers,
})

html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  html, body {{ margin: 0; padding: 0; font-family: -apple-system, sans-serif; }}
  #chart {{ width: 100%; height: 800px; position: relative; }}
  .legend {{
    position: absolute; left: 10px; z-index: 10;
    font-size: 11px; background: rgba(255,255,255,0.92);
    border: 1px solid #ddd; border-radius: 3px; padding: 3px 7px;
    line-height: 1.5;
  }}
  .legend .item {{ display: inline-block; margin-right: 8px; }}
  .legend .swatch {{
    display: inline-block; width: 10px; height: 2px; vertical-align: middle;
    margin-right: 3px;
  }}
</style>
<script src="https://unpkg.com/lightweight-charts@5.0.7/dist/lightweight-charts.standalone.production.js"></script>
</head>
<body>
<div id="chart"></div>
<div class="legend" id="legend-k" style="top: 6px;">MA5 / MA20</div>
<div class="legend" id="legend-vol" style="top: 430px;">成交量</div>
<div class="legend" id="legend-kd" style="top: 545px;">K / D</div>
<div class="legend" id="legend-macd" style="top: 690px;">MACD</div>

<script>
const D = {payload_json};

const chart = LightweightCharts.createChart(document.getElementById('chart'), {{
  layout: {{ background: {{ type: 'solid', color: 'white' }}, textColor: '#222', fontSize: 12,
            panes: {{ separatorColor: '#cfcfcf', separatorHoverColor: 'rgba(0,0,0,0.1)' }} }},
  grid: {{ vertLines: {{ color: '#eef0f3' }}, horzLines: {{ color: '#eef0f3' }} }},
  crosshair: {{
    mode: 0,
    vertLine: {{ width: 1, color: '#1f3a5f', style: 0,
                labelBackgroundColor: '#1f3a5f' }},
    horzLine: {{ width: 1, color: '#aaa', style: 1,
                labelBackgroundColor: '#1f3a5f' }},
  }},
  rightPriceScale: {{ borderColor: '#ccc' }},
  timeScale: {{ borderColor: '#ccc' }},
}});

// v5 API: chart.addSeries(SeriesType, options, paneIndex)
const LWC = LightweightCharts;

// Pane 0 (default): K + MA
const candleSeries = chart.addSeries(LWC.CandlestickSeries, {{
  upColor: '#d62728', downColor: '#26a65b',
  wickUpColor: '#d62728', wickDownColor: '#26a65b',
  borderVisible: false, priceLineVisible: false, lastValueVisible: true,
}});
candleSeries.setData(D.candle);
// v5 markers API
LWC.createSeriesMarkers(candleSeries, D.markers);

const ma5Series = chart.addSeries(LWC.LineSeries, {{ color: '#ff8c00', lineWidth: 1.5,
                                                    priceLineVisible: false, lastValueVisible: false }});
ma5Series.setData(D.ma5);
const ma20Series = chart.addSeries(LWC.LineSeries, {{ color: '#2962ff', lineWidth: 1.5,
                                                     priceLineVisible: false, lastValueVisible: false }});
ma20Series.setData(D.ma20);

// Pane 1: Volume
const volSeries = chart.addSeries(LWC.HistogramSeries, {{
  priceFormat: {{ type: 'volume' }},
}}, 1);
volSeries.setData(D.vol);

// Pane 2: KD
const kSeries = chart.addSeries(LWC.LineSeries, {{ color: '#d62728', lineWidth: 1.5,
                                                  priceLineVisible: false, lastValueVisible: true }}, 2);
kSeries.setData(D.k);
const dSeries = chart.addSeries(LWC.LineSeries, {{ color: '#2962ff', lineWidth: 1.5,
                                                  priceLineVisible: false, lastValueVisible: true }}, 2);
dSeries.setData(D.d);

// Pane 3: MACD
const histSeries = chart.addSeries(LWC.HistogramSeries, {{
  priceFormat: {{ type: 'price', precision: 3, minMove: 0.001 }},
}}, 3);
histSeries.setData(D.macd_hist);
const difSeries = chart.addSeries(LWC.LineSeries, {{ color: '#2962ff', lineWidth: 1.5,
                                                    priceLineVisible: false, lastValueVisible: false }}, 3);
difSeries.setData(D.macd_dif);
const sigSeries = chart.addSeries(LWC.LineSeries, {{ color: '#ff8c00', lineWidth: 1.5,
                                                    priceLineVisible: false, lastValueVisible: false }}, 3);
sigSeries.setData(D.macd_sig);

// Pane heights (v5 API: chart.panes()[i].setHeight)
function setPaneHeights() {{
  try {{
    const panes = chart.panes();
    if (panes.length >= 4) {{
      panes[0].setHeight(420);
      panes[1].setHeight(110);
      panes[2].setHeight(140);
      panes[3].setHeight(140);
    }}
  }} catch(e) {{ console.warn('setPaneHeights failed', e); }}
}}
setTimeout(setPaneHeights, 100);

// Live legend update
function updateLegends(time) {{
  function find(arr) {{ return arr.find(x => x.time === time); }}
  if (!time) {{
    document.getElementById('legend-k').innerHTML =
      '<span class="item"><span class="swatch" style="background:#ff8c00"></span>MA5</span>' +
      '<span class="item"><span class="swatch" style="background:#2962ff"></span>MA20</span>';
    document.getElementById('legend-kd').innerHTML =
      '<span class="item"><span class="swatch" style="background:#d62728"></span>K</span>' +
      '<span class="item"><span class="swatch" style="background:#2962ff"></span>D</span>';
    document.getElementById('legend-macd').innerHTML =
      '<span class="item"><span class="swatch" style="background:#2962ff"></span>DIF</span>' +
      '<span class="item"><span class="swatch" style="background:#ff8c00"></span>MACD</span>';
    document.getElementById('legend-vol').innerHTML = '成交量';
    return;
  }}
  const c = find(D.candle), m5 = find(D.ma5), m20 = find(D.ma20);
  let html = '';
  if (c) html += `<span class="item"><b>${{time}}</b> 開${{c.open}} 高${{c.high}} 低${{c.low}} 收${{c.close}}</span>`;
  if (m5) html += `<span class="item"><span class="swatch" style="background:#ff8c00"></span>MA5 ${{m5.value.toFixed(2)}}</span>`;
  if (m20) html += `<span class="item"><span class="swatch" style="background:#2962ff"></span>MA20 ${{m20.value.toFixed(2)}}</span>`;
  document.getElementById('legend-k').innerHTML = html;

  const v = find(D.vol);
  document.getElementById('legend-vol').innerHTML = v ? `量 ${{Math.round(v.value).toLocaleString()}}` : '成交量';

  const k_v = find(D.k), d_v = find(D.d);
  let kd_html = '';
  if (k_v) kd_html += `<span class="item"><span class="swatch" style="background:#d62728"></span>K ${{k_v.value.toFixed(1)}}</span>`;
  if (d_v) kd_html += `<span class="item"><span class="swatch" style="background:#2962ff"></span>D ${{d_v.value.toFixed(1)}}</span>`;
  document.getElementById('legend-kd').innerHTML = kd_html || 'KD';

  const dif = find(D.macd_dif), sig = find(D.macd_sig), h = find(D.macd_hist);
  let mh = '';
  if (h) mh += `<span class="item">柱 ${{h.value.toFixed(3)}}</span>`;
  if (dif) mh += `<span class="item"><span class="swatch" style="background:#2962ff"></span>DIF ${{dif.value.toFixed(3)}}</span>`;
  if (sig) mh += `<span class="item"><span class="swatch" style="background:#ff8c00"></span>MACD ${{sig.value.toFixed(3)}}</span>`;
  document.getElementById('legend-macd').innerHTML = mh || 'MACD';
}}
chart.subscribeCrosshairMove(p => updateLegends(p && p.time ? p.time : null));
updateLegends(null);

window.addEventListener('resize', () => {{
  chart.applyOptions({{ width: document.getElementById('chart').clientWidth }});
}});
chart.timeScale().fitContent();
</script>
</body>
</html>
"""

components.html(html, height=820, scrolling=False)

st.markdown("---")
st.markdown(
    """
**v5 native pane 應該解決所有問題**：
- ✅ 跨 pane 貫穿線（單一 chart 內建）
- ✅ 時間軸對齊（單一 timeScale）
- ✅ 各 pane 寬度一致（共用底層繪圖區）
- ✅ legend 即時更新
"""
)
