"""Dynamic universe resolver: build universe lists at runtime from TWSE/ETF data."""
from __future__ import annotations

from . import twse_fetcher, etf_components

# Group definitions for industry-based dynamic universes
INDUSTRY_GROUPS: dict[str, dict] = {
    "all_listed": {
        "label": "全部上市",
        "filter": lambda c: c["market"] == "TWSE",
    },
    "all_otc": {
        "label": "全部上櫃",
        "filter": lambda c: c["market"] == "TPEx",
    },
    "all_market": {
        "label": "全部上市櫃（~2000 檔，慢）",
        "filter": lambda c: True,
    },
    "ind_semi": {
        "label": "半導體業",
        "filter": lambda c: "半導體" in c["industry"],
    },
    "ind_electronic_components": {
        "label": "電子零組件",
        "filter": lambda c: "電子零組件" in c["industry"],
    },
    "ind_optoelectronic": {
        "label": "光電業",
        "filter": lambda c: "光電" in c["industry"],
    },
    "ind_computer": {
        "label": "電腦及週邊",
        "filter": lambda c: "電腦" in c["industry"],
    },
    "ind_communication": {
        "label": "通信網路",
        "filter": lambda c: "通信" in c["industry"],
    },
    "ind_finance": {
        "label": "金融保險",
        "filter": lambda c: "金融" in c["industry"],
    },
    "ind_shipping": {
        "label": "航運業",
        "filter": lambda c: "航運" in c["industry"],
    },
    "ind_biotech": {
        "label": "生技醫療",
        "filter": lambda c: "生技" in c["industry"],
    },
    "ind_steel": {
        "label": "鋼鐵工業",
        "filter": lambda c: "鋼鐵" in c["industry"],
    },
    "ind_textile": {
        "label": "紡織纖維",
        "filter": lambda c: "紡織" in c["industry"],
    },
    "ind_tourism": {
        "label": "觀光餐旅",
        "filter": lambda c: "觀光" in c["industry"],
    },
    "ind_construction": {
        "label": "建材營造",
        "filter": lambda c: "建材" in c["industry"],
    },
    "ind_chemical": {
        "label": "化學工業",
        "filter": lambda c: "化學" in c["industry"],
    },
    "ind_energy": {
        "label": "油電燃氣",
        "filter": lambda c: "油電" in c["industry"],
    },
}

# Universe size cap to prevent OOM / yfinance flood
DYNAMIC_LIMIT = 1500


def list_groups() -> list[tuple[str, str]]:
    """Return [(key, label), ...] for industry/market dynamic universes."""
    return [(k, v["label"]) for k, v in INDUSTRY_GROUPS.items()]


def list_etfs() -> list[tuple[str, str]]:
    return etf_components.list_etfs()


def resolve_industry_group(key: str, force_refresh: bool = False) -> list[dict]:
    """Resolve key like 'ind_semi' or 'all_listed' to list[{symbol, name}]."""
    grp = INDUSTRY_GROUPS.get(key)
    if not grp:
        return []
    companies = twse_fetcher.fetch_all(force=force_refresh)
    filtered = [c for c in companies if grp["filter"](c)]
    return [{"symbol": c["symbol"], "name": c["name"]} for c in filtered[:DYNAMIC_LIMIT]]


def resolve_etf(etf_key: str) -> list[dict]:
    """Resolve ETF key like '0056' to component list."""
    name_lookup = _name_lookup_cached()
    return etf_components.get_etf_universe(etf_key, name_lookup)


def _name_lookup_cached() -> dict[str, str]:
    """{symbol -> 公司簡稱} for prettier display in ETF universes."""
    try:
        companies = twse_fetcher.fetch_all()
        return {c["symbol"]: c["name"] for c in companies}
    except Exception:
        return {}
