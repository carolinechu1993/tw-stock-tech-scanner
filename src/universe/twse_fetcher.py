"""Fetch listed (TWSE) and OTC (TPEx) company lists from official OpenAPI.

Cached locally as JSON; refreshed once per day to avoid hammering the API.
"""
from __future__ import annotations
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import urllib.request

CACHE_DIR = Path("cache")
TWSE_URL = "https://openapi.twse.com.tw/v1/opendata/t187ap03_L"
TPEX_URL = "https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_O"

# 產業別代碼 -> 中文名（台股交易所通用對照）
INDUSTRY_CODE_MAP = {
    "01": "水泥工業", "02": "食品工業", "03": "塑膠工業", "04": "紡織纖維",
    "05": "電機機械", "06": "電器電纜", "07": "化學工業", "08": "玻璃陶瓷",
    "09": "造紙工業", "10": "鋼鐵工業", "11": "橡膠工業", "12": "汽車工業",
    "13": "電子工業", "14": "建材營造", "15": "航運業", "16": "觀光餐旅",
    "17": "金融保險", "18": "貿易百貨", "19": "綜合", "20": "其他",
    "21": "化學工業", "22": "生技醫療", "23": "油電燃氣", "24": "半導體業",
    "25": "電腦及週邊設備業", "26": "光電業", "27": "通信網路業",
    "28": "電子零組件業", "29": "電子通路業", "30": "資訊服務業",
    "31": "其他電子業", "32": "文化創意業", "33": "農業科技業",
    "34": "電子商務", "35": "綠能環保", "36": "數位雲端",
    "37": "運動休閒", "38": "居家生活", "80": "管理股票",
}


def _http_get_json(url: str, timeout: int = 30) -> list:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _cache_path(market: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{market}_companies.json"


def _is_fresh(p: Path, max_age_hours: int = 24) -> bool:
    if not p.exists():
        return False
    mtime = datetime.fromtimestamp(p.stat().st_mtime)
    return datetime.now() - mtime < timedelta(hours=max_age_hours)


def _normalize_twse(raw: list) -> list[dict]:
    out = []
    for r in raw:
        code = (r.get("公司代號") or "").strip()
        if not code or not code.isdigit():
            continue
        out.append({
            "code": code,
            "name": (r.get("公司簡稱") or "").strip(),
            "industry_code": (r.get("產業別") or "").strip(),
            "industry": INDUSTRY_CODE_MAP.get((r.get("產業別") or "").strip(), "其他"),
            "market": "TWSE",
            "symbol": f"{code}.TW",
        })
    return out


def _normalize_tpex(raw: list) -> list[dict]:
    out = []
    for r in raw:
        code = (r.get("SecuritiesCompanyCode") or "").strip()
        if not code or not code.isdigit():
            continue
        out.append({
            "code": code,
            "name": (r.get("CompanyAbbreviation") or "").strip(),
            "industry_code": (r.get("SecuritiesIndustryCode") or "").strip(),
            "industry": INDUSTRY_CODE_MAP.get(
                (r.get("SecuritiesIndustryCode") or "").strip(), "其他"),
            "market": "TPEx",
            "symbol": f"{code}.TWO",
        })
    return out


def fetch_listed(force: bool = False) -> list[dict]:
    """Fetch all TWSE-listed companies. Returns list of {code, name, industry, symbol, market}."""
    cache = _cache_path("twse")
    if not force and _is_fresh(cache):
        return json.loads(cache.read_text(encoding="utf-8"))
    raw = _http_get_json(TWSE_URL)
    out = _normalize_twse(raw)
    cache.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def fetch_otc(force: bool = False) -> list[dict]:
    """Fetch all TPEx-listed (上櫃) companies."""
    cache = _cache_path("tpex")
    if not force and _is_fresh(cache):
        return json.loads(cache.read_text(encoding="utf-8"))
    raw = _http_get_json(TPEX_URL)
    out = _normalize_tpex(raw)
    cache.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def fetch_all(force: bool = False) -> list[dict]:
    """Listed + OTC combined."""
    return fetch_listed(force) + fetch_otc(force)


def by_industry(companies: list[dict], industry_keywords: list[str]) -> list[dict]:
    """Filter companies whose industry matches any keyword (substring match)."""
    return [
        c for c in companies
        if any(kw in c.get("industry", "") for kw in industry_keywords)
    ]


def to_universe(companies: list[dict], limit: Optional[int] = None) -> list[dict]:
    """Convert company records to scanner-compatible universe items."""
    items = [{"symbol": c["symbol"], "name": c["name"]} for c in companies]
    if limit:
        items = items[:limit]
    return items


if __name__ == "__main__":
    print("Fetching TWSE listed companies...")
    listed = fetch_listed(force=True)
    print(f"  {len(listed)} companies")
    print("Fetching TPEx OTC companies...")
    otc = fetch_otc(force=True)
    print(f"  {len(otc)} companies")
    industries = {}
    for c in listed + otc:
        industries[c["industry"]] = industries.get(c["industry"], 0) + 1
    print("\nIndustry distribution:")
    for k, v in sorted(industries.items(), key=lambda x: -x[1])[:15]:
        print(f"  {k}: {v}")
