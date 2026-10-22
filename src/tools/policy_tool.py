"""
Refund War Room - Policy Tool.
Retrieves policies with effective date checking, superseded status detection, and authority rank.
"""
import json
from pathlib import Path
from typing import Dict, Any, Optional

from src.config import DOCS_PATH, AUTHORITY_HIERARCHY


def get_policy(name: str, as_of_date: Optional[str] = None, docs_path: Path = DOCS_PATH) -> Dict[str, Any]:
    """Retrieves policy document by name or doc_id and evaluates validity as of specified date."""
    if Path(docs_path).exists():
        with open(docs_path, "r", encoding="utf-8") as f:
            docs = json.load(f)
    else:
        from src.data.documents import DOCUMENTS
        docs = DOCUMENTS

    cleaned_name = name.strip().lower()

    # Search for matching policy
    matched_doc: Optional[Dict[str, Any]] = None
    for doc in docs:
        if doc.get("doc_id", "").lower() == cleaned_name:
            matched_doc = doc
            break

    if not matched_doc:
        for doc in docs:
            if cleaned_name in doc.get("title", "").lower() or cleaned_name in doc.get("category", "").lower():
                matched_doc = doc
                break

    if not matched_doc:
        return {
            "status": "not_found",
            "policy_name": name,
            "as_of_date": as_of_date,
            "error": f"Policy '{name}' not found in registry."
        }

    # Evaluate active status as of date
    effective_date = matched_doc.get("effective_date")
    end_date = matched_doc.get("end_date")
    superseded_by = matched_doc.get("superseded_by")

    is_active = True
    status_note = "Active"

    if as_of_date:
        if effective_date and as_of_date < effective_date:
            is_active = False
            status_note = f"Policy not yet effective as of {as_of_date} (effective: {effective_date})"
        elif end_date and as_of_date > end_date:
            is_active = False
            status_note = f"Policy superseded as of {end_date} by {superseded_by or 'newer revision'}"
        elif end_date and as_of_date <= end_date:
            is_active = True
            status_note = f"Active on {as_of_date} (prior to {end_date} sunset)"
        elif superseded_by:
            status_note = f"Superseded by {superseded_by}"
            is_active = False
    elif superseded_by:
        is_active = False
        status_note = f"Superseded by {superseded_by}"

    authority = matched_doc.get("authority", "Customer Support Guidelines")
    source_rank = AUTHORITY_HIERARCHY.get(authority, matched_doc.get("source_rank", 10))

    return {
        "status": "success",
        "doc_id": matched_doc.get("doc_id"),
        "title": matched_doc.get("title"),
        "category": matched_doc.get("category"),
        "authority": authority,
        "source_rank": source_rank,
        "effective_date": effective_date,
        "end_date": end_date,
        "superseded_by": superseded_by,
        "is_active_as_of_date": is_active,
        "status_note": status_note,
        "content": matched_doc.get("content"),
        "tainted": True  # All retrieved text is treated as untrusted data
    }
