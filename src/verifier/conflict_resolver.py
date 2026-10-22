"""
Refund War Room - Conflict Resolver.
Resolves policy conflicts deterministically using Source Authority Hierarchy,
Effective Dates, and Recency.
"""
from typing import Dict, Any, List, Optional
from src.config import AUTHORITY_HIERARCHY


def get_authority_rank(authority_str: str) -> int:
    return AUTHORITY_HIERARCHY.get(authority_str, 10)


def resolve_policy_conflict(
    policy_a: Dict[str, Any],
    policy_b: Dict[str, Any],
    as_of_date: Optional[str] = None
) -> Dict[str, Any]:
    """Resolves a conflict between two policies deterministically:
    1. Check Superseded status (superseded loses automatically)
    2. Authority Rank (Higher rank wins)
    3. Recency / Effective Date (Newer wins if authority is equal)
    4. Unresolved if tied
    """
    id_a = policy_a.get("doc_id", "Policy_A")
    id_b = policy_b.get("doc_id", "Policy_B")

    # Step 1: Check superseded
    if policy_a.get("superseded_by") == id_b:
        return {
            "resolved": True,
            "winner": id_b,
            "loser": id_a,
            "rule": "SUPERSEDED_REVISION",
            "explanation": f"{id_a} was superseded by {id_b}."
        }
    if policy_b.get("superseded_by") == id_a:
        return {
            "resolved": True,
            "winner": id_a,
            "loser": id_b,
            "rule": "SUPERSEDED_REVISION",
            "explanation": f"{id_b} was superseded by {id_a}."
        }

    # Step 2: Source Authority Rank
    rank_a = policy_a.get("source_rank") or get_authority_rank(policy_a.get("authority", ""))
    rank_b = policy_b.get("source_rank") or get_authority_rank(policy_b.get("authority", ""))

    if rank_a > rank_b:
        return {
            "resolved": True,
            "winner": id_a,
            "loser": id_b,
            "rule": "SOURCE_AUTHORITY_HIERARCHY",
            "explanation": f"{id_a} authority ({policy_a.get('authority')} [rank {rank_a}]) overrides {id_b} ({policy_b.get('authority')} [rank {rank_b}])."
        }
    elif rank_b > rank_a:
        return {
            "resolved": True,
            "winner": id_b,
            "loser": id_a,
            "rule": "SOURCE_AUTHORITY_HIERARCHY",
            "explanation": f"{id_b} authority ({policy_b.get('authority')} [rank {rank_b}]) overrides {id_a} ({policy_a.get('authority')} [rank {rank_a}])."
        }

    # Step 3: Recency / Effective Date
    eff_a = policy_a.get("effective_date", "1970-01-01")
    eff_b = policy_b.get("effective_date", "1970-01-01")

    if eff_a > eff_b:
        return {
            "resolved": True,
            "winner": id_a,
            "loser": id_b,
            "rule": "RECENCY_EFFECTIVE_DATE",
            "explanation": f"{id_a} has a newer effective date ({eff_a}) than {id_b} ({eff_b}) at equal authority."
        }
    elif eff_b > eff_a:
        return {
            "resolved": True,
            "winner": id_b,
            "loser": id_a,
            "rule": "RECENCY_EFFECTIVE_DATE",
            "explanation": f"{id_b} has a newer effective date ({eff_b}) than {id_a} ({eff_a}) at equal authority."
        }

    # Step 4: True Tie
    return {
        "resolved": False,
        "winner": None,
        "loser": None,
        "rule": "TIED_CONFLICT_ESCALATION",
        "explanation": f"Unresolvable tie between {id_a} and {id_b} with identical authority and effective dates. Human escalation required."
    }
