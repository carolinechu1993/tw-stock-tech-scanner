# 台股技術分析掃描器

依多項技術分析指標的「命中數」排序台股，找出符合多個進場條件的標的。**僅供技術分析教學與研究輔助，不構成投資建議**。

## 主要功能

- **19 條進場規則**，分為兩派：
  - **綜合派**（11 條）：均線黃金交叉、MACD、ADX、KD、RSI、爆量突破、量價齊揚、OBV、布林上下軌、ATR
  - **朱家泓派**（8 條）：均線多頭排列、均線糾結突破、回檔不破月線、量縮回檔紅K放量、長紅K突破、長下影線、變盤線、底部第二隻腳
- 規則可**自由勾選**，按「綜合派 / 朱家泓派」一鍵切換
- 7 組預設股票池（測試組、半導體、航運、金融、AI 伺服器、短線熱門股、0050 前 20）
- 個股詳情：K 線 + 均線 + 布林通道 + 成交量 + KD + MACD 子圖
- 純命中數計分（不含主觀權重）

## 線上版

> 部署到 Streamlit Cloud 後在此貼上網址

## 本機執行

```bash
pip install -r requirements.txt
streamlit run ui/app.py
```

瀏覽器開 `http://localhost:8501`。

## CLI 版

不開 dashboard 直接輸出 CSV 排行榜：
```bash
python -m src.scanner test_10
# 結果存到 cache/ranking_test_10.csv
```

可用 universe key：`test_10`、`semiconductor`、`shipping`、`finance`、`ai_server`、`popular_short`、`etf_0050_top20`（在 `config.yaml` 可改）。

## 專案結構

```
src/
├── scanner.py            主流程
├── data/                 資料層（yfinance + parquet 快取）
├── indicators/           純 pandas 實作的技術指標
└── signals/              19 條規則 + 計分 + 中文標籤
ui/app.py                 Streamlit dashboard
tests/                    指標單元測試
config.yaml               股票池、指標參數、規則設定
```

## 技術細節

- **資料源**：yfinance（延遲約 15-20 分鐘）
- **指標實作**：純 pandas/numpy，台股 KD 採 9-3-3 公式（K_t = 2/3·K_{t-1} + 1/3·RSV_t）
- **計分**：純命中數，每條規則平等對待（不含權重，避免未經回測的主觀偏差）
- **快取**：本地 parquet（60 分鐘 TTL）

## ⚠️ 免責聲明

- 本工具僅為**技術分析教學與研究輔助**，所有資料延遲約 15-20 分鐘且可能有錯誤
- **不構成任何投資建議或推薦**，投資決策與盈虧由使用者完全自負
- 過往技術訊號**不保證**未來績效
- 不為使用本工具產生的任何虧損、損害或交易結果負責

## 授權

僅供個人學習用途。
