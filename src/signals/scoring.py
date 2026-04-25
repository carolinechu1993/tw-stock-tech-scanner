from typing import Dict, List
import pandas as pd

from .rules import RULES, RuleResult


def evaluate(df: pd.DataFrame, indicator_params: dict, rule_config: dict) -> Dict[str, RuleResult]:
    results: Dict[str, RuleResult] = {}
    for name, cfg in rule_config.items():
        if not cfg.get("enabled", True):
            continue
        rule_fn = RULES.get(name)
        if rule_fn is None:
            continue
        try:
            results[name] = rule_fn(df, indicator_params)
        except Exception as e:
            results[name] = RuleResult(False, 0.0, f"error: {e}")
    return results


def score(results: Dict[str, RuleResult], rule_config: dict) -> dict:
    """Pure hit-count scoring: every rule counts as 1, no weights."""
    hit_rules: List[str] = []
    by_cat: Dict[str, int] = {}
    for name, r in results.items():
        if r.hit:
            hit_rules.append(name)
            cat = rule_config.get(name, {}).get("category", "other")
            by_cat[cat] = by_cat.get(cat, 0) + 1
    return {
        "hits": len(hit_rules),
        "by_category": by_cat,
        "hit_rules": hit_rules,
    }


def to_dataframe(rows: List[dict]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    return df.sort_values("hits", ascending=False).reset_index(drop=True)
