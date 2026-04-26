"""Chinese display labels and explanations for rule IDs, categories, schools."""

RULE_LABELS = {
    # 多頭 — 綜合派
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
    # 多頭 — 朱家泓派
    "ma_bullish_alignment":    "均線多頭排列",
    "ma_converge_breakout":    "均線糾結突破",
    "pullback_holds_ma20":     "回檔不破月線",
    "volume_dry_red_surge":    "量縮回檔後紅K放量",
    "long_red_breakout":       "長紅K突破",
    "long_lower_shadow":       "長下影線止跌",
    "doji_or_spinning_top":    "變盤線（十字／紡錘）",
    "double_bottom":           "底部第二隻腳",
    # 空頭 — 反向訊號（出場/做空）
    "ma_death_cross":          "均線死亡交叉",
    "ma_bearish_alignment":    "均線空頭排列",
    "ma_converge_breakdown":   "均線糾結跌破",
    "rebound_caps_ma20":       "反彈不過月線",
    "macd_hist_turn_negative": "MACD 柱翻綠",
    "adx_strong_downtrend":    "ADX 強勢空頭",
    "kd_overbought_dead":      "KD 高檔死亡交叉",
    "rsi_overbought_drop":     "RSI 跌出超買",
    "volume_breakdown":        "爆量下跌",
    "price_volume_collapse":   "量增價跌",
    "obv_new_low":             "OBV 創新低",
    "volume_dry_black_surge":  "量縮反彈後黑K放量",
    "bbands_upper_reject":     "布林上軌反壓",
    "bbands_lower_break":      "跌破布林下軌",
    "long_black_breakdown":    "長黑K跌破",
    "long_upper_shadow":       "長上影線止漲",
    "double_top":              "頂部第二肩（M頭）",
}

# 規則方向：bullish（進場）/ bearish（出場）/ neutral（雙向通用）
RULE_DIRECTION = {
    # 多頭
    "ma_golden_cross": "bullish",
    "macd_hist_turn_positive": "bullish",
    "adx_strong_uptrend": "bullish",
    "kd_oversold_golden": "bullish",
    "rsi_recover": "bullish",
    "volume_breakout": "bullish",
    "price_volume_surge": "bullish",
    "obv_new_high": "bullish",
    "bbands_lower_bounce": "bullish",
    "bbands_upper_break": "bullish",
    "ma_bullish_alignment": "bullish",
    "ma_converge_breakout": "bullish",
    "pullback_holds_ma20": "bullish",
    "volume_dry_red_surge": "bullish",
    "long_red_breakout": "bullish",
    "long_lower_shadow": "bullish",
    "double_bottom": "bullish",
    # 空頭
    "ma_death_cross": "bearish",
    "ma_bearish_alignment": "bearish",
    "ma_converge_breakdown": "bearish",
    "rebound_caps_ma20": "bearish",
    "macd_hist_turn_negative": "bearish",
    "adx_strong_downtrend": "bearish",
    "kd_overbought_dead": "bearish",
    "rsi_overbought_drop": "bearish",
    "volume_breakdown": "bearish",
    "price_volume_collapse": "bearish",
    "obv_new_low": "bearish",
    "volume_dry_black_surge": "bearish",
    "bbands_upper_reject": "bearish",
    "bbands_lower_break": "bearish",
    "long_black_breakdown": "bearish",
    "long_upper_shadow": "bearish",
    "double_top": "bearish",
    # 雙向
    "atr_expansion": "neutral",
    "doji_or_spinning_top": "neutral",
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
        "summary": "趨勢由空轉多",
        "what": "短期均線（MA5）由下往上穿越中期均線（MA20）。",
        "meaning": "近期股價強度勝過過去一個月平均，趨勢由空轉多。",
        "caveat": "盤整時容易出現假交叉；建議搭配量能放大確認。",
    },
    "macd_hist_turn_positive": {
        "summary": "動能翻多",
        "what": "MACD 柱狀圖（DIF − Signal）由負轉正。",
        "meaning": "短期動能開始勝過長期動能，多頭力量浮現。",
        "caveat": "在橫盤行情會頻繁翻紅翻黑，雜訊較多。",
    },
    "adx_strong_uptrend": {
        "summary": "強多頭趨勢成立",
        "what": "ADX > 25 且 +DI > −DI（多方力道強於空方）。",
        "meaning": "趨勢已成立且偏多，適合順勢操作。",
        "caveat": "ADX 只反映「趨勢強度」不分多空，必須搭配 +DI/−DI 判斷方向。",
    },
    "kd_oversold_golden": {
        "summary": "超賣反彈訊號",
        "what": "K 值在 30 以下時，K 由下往上穿越 D。",
        "meaning": "短線跌深超賣後反轉，常見的短期反彈起點。",
        "caveat": "強勢下跌中 KD 可能在低檔反覆「鈍化」，連續黃金交叉但股價續跌。",
    },
    "rsi_recover": {
        "summary": "脫離超賣區",
        "what": "RSI 近 5 日曾跌破 30，目前回到 40 以上。",
        "meaning": "從超賣區走出，動能轉強。",
        "caveat": "強勢上漲中 RSI 可能從 50+ 直接起跳，這條訊號會錯過。",
    },
    "volume_breakout": {
        "summary": "爆量起漲",
        "what": "當日成交量 ≥ 5 日均量 × 1.5，且收紅。",
        "meaning": "資金大舉進場推升股價，常見漲勢起點或關鍵突破。",
        "caveat": "若伴隨重大利空消息可能是「逃命量」，要看消息面。",
    },
    "price_volume_surge": {
        "summary": "量價齊揚",
        "what": "收盤上漲且成交量比前一日增加超過 10%。",
        "meaning": "量價齊揚是健康的多頭結構，無量上漲較易回檔。",
        "caveat": "高檔量增可能是出貨，需配合趨勢位置判斷。",
    },
    "obv_new_high": {
        "summary": "籌碼累積創高",
        "what": "OBV（能量潮指標，價漲累計量、價跌扣減量）創 20 日新高。",
        "meaning": "資金累積流入創高，籌碼面強勢。",
        "caveat": "OBV 是長期累積值，短期波段不易顯著反映變化。",
    },
    "bbands_lower_bounce": {
        "summary": "極端跌幅反彈",
        "what": "前一日最低點觸及或跌破布林下軌，今日收紅反彈。",
        "meaning": "統計上股價極端跌幅後的均值回歸（mean reversion）。",
        "caveat": "強趨勢下跌中沿著下軌「破軌」下殺，此訊號會連續失效。",
    },
    "bbands_upper_break": {
        "summary": "突破超漲區",
        "what": "收盤價高於布林上軌（突破 +2σ 區間）。",
        "meaning": "股價脫離常態波動範圍，動能極強。",
        "caveat": "突破也可能是末升段；需配合量能判斷真假突破。",
    },
    "atr_expansion": {
        "summary": "波動率放大",
        "what": "當日 ATR ≥ 20 日均 ATR × 1.3。",
        "meaning": "波動率放大代表市場關注度提升，常出現在趨勢啟動或反轉時。",
        "caveat": "純波動指標沒有方向性，必須配合趨勢/動能訊號使用。",
    },
    # 朱家泓派
    "ma_bullish_alignment": {
        "summary": "完美多頭排列",
        "what": "MA5 > MA10 > MA20 > MA60，且四條均線當日值都比前一日高（皆上揚）。",
        "meaning": "短中長期趨勢全面同向轉多，朱老師認為這是順勢做多最安全的結構。",
        "caveat": "排列形成後可能已漲一段，追入要評估離 MA20 的乖離率，避免追高。",
    },
    "ma_converge_breakout": {
        "summary": "糾結後起漲",
        "what": "MA5/10/20 三條均線連續 5 日收斂（最大 spread < 2%），今日紅K且收盤突破前 5 日高。",
        "meaning": "朱老師最重視的「起漲訊號」— 均線糾結後的突破代表盤整結束、新趨勢啟動。",
        "caveat": "突破需放量才可信；若無量突破可能是假突破，隔日易回測糾結區。",
    },
    "pullback_holds_ma20": {
        "summary": "守月線整理",
        "what": "MA20 > MA60（多頭結構）且近 10 日內有回檔（高低差 ≥3%），但收盤從未跌破 MA20。",
        "meaning": "多頭整理結構健康，月線守住代表主力沒跑，回升機率高。",
        "caveat": "守住月線只是必要條件不是充分條件；還要看回升時是否有量。",
    },
    "volume_dry_red_surge": {
        "summary": "縮量後攻擊",
        "what": "前 2-3 日量縮且至少一日下跌（量縮回檔），今日紅K + 站上 MA5 + 量能 ≥ 前日 1.5 倍。",
        "meaning": "朱老師經典進場組合 — 量縮回檔到支撐後，量增紅K是主力重新進場的訊號。",
        "caveat": "若回檔已破 MA20 或 MA60 則此訊號意義打折，需重新評估趨勢。",
    },
    "long_red_breakout": {
        "summary": "長紅突破",
        "what": "K 棒實體 ≥ ATR(14) × 1.5、紅K（收 > 開），且收盤突破前 5 日最高。",
        "meaning": "強勢長紅突破代表多方一棒打穿賣壓，後續延續性高。",
        "caveat": "若伴隨利多新聞可能是消息面拉抬，隔日要看是否能站穩；無利多的長紅較可信。",
    },
    "long_lower_shadow": {
        "summary": "下影線止跌",
        "what": "下影線長度 ≥ 實體 × 2，且出現於下跌段（5 日內走弱或收盤低於 MA20）。",
        "meaning": "盤中跌深後被買盤強力承接，常見短線止跌訊號。",
        "caveat": "需要隔日紅K+不破前低確認；若隔日續跌破今日低點則訊號失效。",
    },
    "doji_or_spinning_top": {
        "summary": "多空均衡警示",
        "what": "K 棒實體小於高低差的 30%，且當日收盤位於近 20 日相對高（前 20%）或低（後 20%）位置。",
        "meaning": "多空力道均衡的變盤訊號，出現在頂部容易反轉向下、出現在底部容易反轉向上。",
        "caveat": "變盤線只是「警示」，需要隔日 K 線確認方向（紅 K 確認反轉、黑 K 否認）。",
    },
    "double_bottom": {
        "summary": "W 底反轉訊號",
        "what": "近 30 日內出現兩個低點，間距 ≥ 5 日、價差 < 5%、第二低 ≥ 第一低，且當前股價已從第二低反彈 2% 以上。",
        "meaning": "經典 W 底反轉型態，第二腳測試成功代表賣壓消化、買盤承接。",
        "caveat": "型態完成需要突破頸線（兩低之間的高點）才正式成立；目前條件只是雛形。",
    },
    # ---------- 空頭/出場訊號 ----------
    "ma_death_cross": {
        "summary": "趨勢由多轉空",
        "what": "短期均線（MA5）由上往下穿越中期均線（MA20）。",
        "meaning": "近期股價弱於過去一個月平均，趨勢轉空，常用作出場/做空訊號。",
        "caveat": "盤整時容易出現假交叉；需配合量增下殺確認。",
    },
    "ma_bearish_alignment": {
        "summary": "完美空頭排列",
        "what": "MA5 < MA10 < MA20 < MA60，且四條均線當日值都比前一日低（皆下行）。",
        "meaning": "短中長期趨勢全面同向轉空，順勢做空最安全的結構。",
        "caveat": "排列形成後可能已跌一段，搶反彈要評估離 MA20 的乖離。",
    },
    "ma_converge_breakdown": {
        "summary": "糾結後起跌",
        "what": "MA5/10/20 三條均線連續 5 日收斂（最大 spread < 2%），今日黑K且收盤跌破前 5 日低。",
        "meaning": "均線糾結後的跌破代表盤整結束、新空頭趨勢啟動。",
        "caveat": "需放量才可信；無量跌破可能是假跌破，隔日易回測糾結區。",
    },
    "rebound_caps_ma20": {
        "summary": "反彈受月線壓",
        "what": "MA20 < MA60（空頭結構）且近 10 日內有反彈（高低差 ≥3%），但收盤從未突破 MA20。",
        "meaning": "空頭整理結構中，月線形成壓力，反彈無力，續跌機率高。",
        "caveat": "壓住月線只是必要條件；若量能放大跌破前低才是強空訊號。",
    },
    "macd_hist_turn_negative": {
        "summary": "動能翻空",
        "what": "MACD 柱狀圖（DIF − Signal）由正轉負。",
        "meaning": "短期動能開始弱於長期動能，空頭力量浮現。",
        "caveat": "在橫盤行情會頻繁翻紅翻綠，雜訊較多。",
    },
    "adx_strong_downtrend": {
        "summary": "強空頭趨勢成立",
        "what": "ADX > 25 且 -DI > +DI（空方力道強於多方）。",
        "meaning": "空頭趨勢已成立且強勢，適合順勢做空 / 避免承接。",
        "caveat": "ADX 只反映「趨勢強度」不分多空，必須搭配 +DI/−DI 判斷方向。",
    },
    "kd_overbought_dead": {
        "summary": "超買回落訊號",
        "what": "K 值在 70 以上時，K 由上往下穿越 D。",
        "meaning": "短線超買後反轉，常見的高檔出場 / 做空訊號。",
        "caveat": "強勢上漲中 KD 可能在高檔反覆鈍化，連續死亡交叉但股價續漲。",
    },
    "rsi_overbought_drop": {
        "summary": "脫離超買區",
        "what": "RSI 近 5 日曾超過 70，目前跌到 60 以下。",
        "meaning": "從超買區走出，動能轉弱。",
        "caveat": "強勢下跌中 RSI 可能直接從 50 以下續跌，會錯過此訊號。",
    },
    "volume_breakdown": {
        "summary": "爆量殺出",
        "what": "當日成交量 ≥ 5 日均量 × 1.5，且收綠。",
        "meaning": "資金大舉出場壓低股價，常見跌勢起點或關鍵跌破，亦稱「逃命量」。",
        "caveat": "若伴隨重大利多消息卻爆量下跌，可能是利多出盡，反而更兇。",
    },
    "price_volume_collapse": {
        "summary": "量增價跌",
        "what": "收盤下跌且成交量比前一日增加超過 10%。",
        "meaning": "高檔量增價跌是出貨訊號；底部量增價跌可能是恐慌賣壓。",
        "caveat": "需要配合趨勢位置判斷（高檔出貨 vs 底部恐慌）。",
    },
    "obv_new_low": {
        "summary": "籌碼持續流出",
        "what": "OBV（能量潮指標）創 20 日新低。",
        "meaning": "資金累積流出創低，籌碼面持續弱勢。",
        "caveat": "OBV 是長期累積值，短期波段不易顯著反映變化。",
    },
    "volume_dry_black_surge": {
        "summary": "縮量反彈後起跌",
        "what": "前 2-3 日量縮且至少一日上漲（量縮反彈），今日黑K + 跌破 MA5 + 量能 ≥ 前日 1.5 倍。",
        "meaning": "縮量反彈後量增黑K是主力重新出貨的訊號。",
        "caveat": "若反彈已突破 MA20 或 MA60，此訊號意義打折，需重新評估趨勢。",
    },
    "bbands_upper_reject": {
        "summary": "上軌反壓",
        "what": "前一日最高觸及或超過布林上軌，今日收黑被壓回。",
        "meaning": "統計上股價極端漲幅後的均值回歸（mean reversion）。",
        "caveat": "強趨勢上漲中沿著上軌「攻軌」上漲，此訊號會連續失效。",
    },
    "bbands_lower_break": {
        "summary": "跌破超跌區",
        "what": "收盤價低於布林下軌（跌破 -2σ 區間）。",
        "meaning": "股價脫離常態波動範圍向下，跌深加速、空方動能極強。",
        "caveat": "跌破也可能是末跌段；需配合量能判斷是真破軌或假破軌。",
    },
    "long_black_breakdown": {
        "summary": "長黑跌破",
        "what": "K 棒實體 ≥ ATR(14) × 1.5、黑K（收 < 開），且收盤跌破前 5 日最低。",
        "meaning": "強勢長黑代表空方一棒打穿支撐，後續延續性高。",
        "caveat": "若伴隨利空新聞可能是消息面殺出，隔日是否能站穩很關鍵。",
    },
    "long_upper_shadow": {
        "summary": "上影線止漲",
        "what": "上影線長度 ≥ 實體 × 2，且出現於上漲段（5 日內走強或收盤高於 MA20）。",
        "meaning": "盤中漲過頭被賣盤打回，常見短線止漲訊號。",
        "caveat": "需要隔日黑K + 跌破前低確認；若隔日續強則訊號失效。",
    },
    "double_top": {
        "summary": "M 頭反轉訊號",
        "what": "近 30 日內出現兩個高點，間距 ≥ 5 日、價差 < 5%、第二高 ≤ 第一高，且當前股價已從第二高回落 2% 以上。",
        "meaning": "經典 M 頭反轉型態，第二肩測試失敗代表買盤耗盡、賣壓抬頭。",
        "caveat": "型態完成需要跌破頸線（兩高之間的低點）才正式成立；目前只是雛形。",
    },
}


def rule_zh(rule_id: str) -> str:
    return RULE_LABELS.get(rule_id, rule_id)


def cat_zh(category: str) -> str:
    return CATEGORY_LABELS.get(category, category)


def school_zh(school: str) -> str:
    return SCHOOL_LABELS.get(school, school)


def rule_desc(rule_id: str) -> dict:
    return RULE_DESCRIPTIONS.get(rule_id, {"summary": "", "what": "", "meaning": "", "caveat": ""})


def rule_summary(rule_id: str) -> str:
    """≤10 字的精簡意義摘要，給 UI 表格用。"""
    return RULE_DESCRIPTIONS.get(rule_id, {}).get("summary", "")


def rule_direction(rule_id: str) -> str:
    """規則方向：bullish / bearish / neutral。"""
    return RULE_DIRECTION.get(rule_id, "neutral")
