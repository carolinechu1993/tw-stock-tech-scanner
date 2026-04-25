"""Chinese display labels and explanations for rule IDs, categories, schools."""

RULE_LABELS = {
    # 綜合派
    "ma_golden_cross":         "均線黃金交叉",
    "macd_hist_turn_positive": "MACD 柱翻紅",
    "adx_strong_uptrend":      "ADX 強勢多頭",
    "kd_oversold_golden":      "KD 低檔黃金交叉",
    "rsi_recover":             "RSI 脫離超賣",
    "volume_breakout":         "爆量突破",
    "price_volume_surge":      "量價齊揚",
    "obv_new_high":            "OBV 創新高",
    "bbands_lower_bounce":     "布林下軌反彈",
    "bbands_upper_break":      "突破布林上軌",
    "atr_expansion":           "ATR 波動擴張",
    # 朱家泓派
    "ma_bullish_alignment":    "均線多頭排列",
    "ma_converge_breakout":    "均線糾結突破",
    "pullback_holds_ma20":     "回檔不破月線",
    "volume_dry_red_surge":    "量縮回檔後紅K放量",
    "long_red_breakout":       "長紅K突破",
    "long_lower_shadow":       "長下影線止跌",
    "doji_or_spinning_top":    "變盤線（十字／紡錘）",
    "double_bottom":           "底部第二隻腳",
}

CATEGORY_LABELS = {
    "trend":      "趨勢",
    "momentum":   "動能",
    "volume":     "量價",
    "volatility": "波動",
    "pattern":    "型態",
}

SCHOOL_LABELS = {
    "general": "綜合派",
    "zhu":     "朱家泓派",
}

RULE_DESCRIPTIONS = {
    "ma_golden_cross": {
        "what": "短期均線（MA5）由下往上穿越中期均線（MA20）。",
        "meaning": "近期股價強度勝過過去一個月平均，趨勢由空轉多。",
        "caveat": "盤整時容易出現假交叉；建議搭配量能放大確認。",
    },
    "macd_hist_turn_positive": {
        "what": "MACD 柱狀圖（DIF − Signal）由負轉正。",
        "meaning": "短期動能開始勝過長期動能，多頭力量浮現。",
        "caveat": "在橫盤行情會頻繁翻紅翻黑，雜訊較多。",
    },
    "adx_strong_uptrend": {
        "what": "ADX > 25 且 +DI > −DI（多方力道強於空方）。",
        "meaning": "趨勢已成立且偏多，適合順勢操作。",
        "caveat": "ADX 只反映「趨勢強度」不分多空，必須搭配 +DI/−DI 判斷方向。",
    },
    "kd_oversold_golden": {
        "what": "K 值在 30 以下時，K 由下往上穿越 D。",
        "meaning": "短線跌深超賣後反轉，常見的短期反彈起點。",
        "caveat": "強勢下跌中 KD 可能在低檔反覆「鈍化」，連續黃金交叉但股價續跌。",
    },
    "rsi_recover": {
        "what": "RSI 近 5 日曾跌破 30，目前回到 40 以上。",
        "meaning": "從超賣區走出，動能轉強。",
        "caveat": "強勢上漲中 RSI 可能從 50+ 直接起跳，這條訊號會錯過。",
    },
    "volume_breakout": {
        "what": "當日成交量 ≥ 5 日均量 × 1.5，且收紅。",
        "meaning": "資金大舉進場推升股價，常見漲勢起點或關鍵突破。",
        "caveat": "若伴隨重大利空消息可能是「逃命量」，要看消息面。",
    },
    "price_volume_surge": {
        "what": "收盤上漲且成交量比前一日增加超過 10%。",
        "meaning": "量價齊揚是健康的多頭結構，無量上漲較易回檔。",
        "caveat": "高檔量增可能是出貨，需配合趨勢位置判斷。",
    },
    "obv_new_high": {
        "what": "OBV（能量潮指標，價漲累計量、價跌扣減量）創 20 日新高。",
        "meaning": "資金累積流入創高，籌碼面強勢。",
        "caveat": "OBV 是長期累積值，短期波段不易顯著反映變化。",
    },
    "bbands_lower_bounce": {
        "what": "前一日最低點觸及或跌破布林下軌，今日收紅反彈。",
        "meaning": "統計上股價極端跌幅後的均值回歸（mean reversion）。",
        "caveat": "強趨勢下跌中沿著下軌「破軌」下殺，此訊號會連續失效。",
    },
    "bbands_upper_break": {
        "what": "收盤價高於布林上軌（突破 +2σ 區間）。",
        "meaning": "股價脫離常態波動範圍，動能極強。",
        "caveat": "突破也可能是末升段；需配合量能判斷真假突破。",
    },
    "atr_expansion": {
        "what": "當日 ATR ≥ 20 日均 ATR × 1.3。",
        "meaning": "波動率放大代表市場關注度提升，常出現在趨勢啟動或反轉時。",
        "caveat": "純波動指標沒有方向性，必須配合趨勢/動能訊號使用。",
    },
    # 朱家泓派
    "ma_bullish_alignment": {
        "what": "MA5 > MA10 > MA20 > MA60，且四條均線當日值都比前一日高（皆上揚）。",
        "meaning": "短中長期趨勢全面同向轉多，朱老師認為這是順勢做多最安全的結構。",
        "caveat": "排列形成後可能已漲一段，追入要評估離 MA20 的乖離率，避免追高。",
    },
    "ma_converge_breakout": {
        "what": "MA5/10/20 三條均線連續 5 日收斂（最大 spread < 2%），今日紅K且收盤突破前 5 日高。",
        "meaning": "朱老師最重視的「起漲訊號」— 均線糾結後的突破代表盤整結束、新趨勢啟動。",
        "caveat": "突破需放量才可信；若無量突破可能是假突破，隔日易回測糾結區。",
    },
    "pullback_holds_ma20": {
        "what": "MA20 > MA60（多頭結構）且近 10 日內有回檔（高低差 ≥3%），但收盤從未跌破 MA20。",
        "meaning": "多頭整理結構健康，月線守住代表主力沒跑，回升機率高。",
        "caveat": "守住月線只是必要條件不是充分條件；還要看回升時是否有量。",
    },
    "volume_dry_red_surge": {
        "what": "前 2-3 日量縮且至少一日下跌（量縮回檔），今日紅K + 站上 MA5 + 量能 ≥ 前日 1.5 倍。",
        "meaning": "朱老師經典進場組合 — 量縮回檔到支撐後，量增紅K是主力重新進場的訊號。",
        "caveat": "若回檔已破 MA20 或 MA60 則此訊號意義打折，需重新評估趨勢。",
    },
    "long_red_breakout": {
        "what": "K 棒實體 ≥ ATR(14) × 1.5、紅K（收 > 開），且收盤突破前 5 日最高。",
        "meaning": "強勢長紅突破代表多方一棒打穿賣壓，後續延續性高。",
        "caveat": "若伴隨利多新聞可能是消息面拉抬，隔日要看是否能站穩；無利多的長紅較可信。",
    },
    "long_lower_shadow": {
        "what": "下影線長度 ≥ 實體 × 2，且出現於下跌段（5 日內走弱或收盤低於 MA20）。",
        "meaning": "盤中跌深後被買盤強力承接，常見短線止跌訊號。",
        "caveat": "需要隔日紅K+不破前低確認；若隔日續跌破今日低點則訊號失效。",
    },
    "doji_or_spinning_top": {
        "what": "K 棒實體小於高低差的 30%，且當日收盤位於近 20 日相對高（前 20%）或低（後 20%）位置。",
        "meaning": "多空力道均衡的變盤訊號，出現在頂部容易反轉向下、出現在底部容易反轉向上。",
        "caveat": "變盤線只是「警示」，需要隔日 K 線確認方向（紅 K 確認反轉、黑 K 否認）。",
    },
    "double_bottom": {
        "what": "近 30 日內出現兩個低點，間距 ≥ 5 日、價差 < 5%、第二低 ≥ 第一低，且當前股價已從第二低反彈 2% 以上。",
        "meaning": "經典 W 底反轉型態，第二腳測試成功代表賣壓消化、買盤承接。",
        "caveat": "型態完成需要突破頸線（兩低之間的高點）才正式成立；目前條件只是雛形。",
    },
}


def rule_zh(rule_id: str) -> str:
    return RULE_LABELS.get(rule_id, rule_id)


def cat_zh(category: str) -> str:
    return CATEGORY_LABELS.get(category, category)


def school_zh(school: str) -> str:
    return SCHOOL_LABELS.get(school, school)


def rule_desc(rule_id: str) -> dict:
    return RULE_DESCRIPTIONS.get(rule_id, {"what": "", "meaning": "", "caveat": ""})
