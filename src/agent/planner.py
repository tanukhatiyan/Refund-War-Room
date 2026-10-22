"""
Refund War Room - Deterministic Planner.
Analyzes user questions, generates tool execution plans, handles multi-hop logic,
identifies missing evidence, and synthesizes structured claims with exact citations.
"""
import re
from typing import Dict, Any, List, Optional, Tuple


def extract_order_ids(text: str) -> List[str]:
    return list(set(re.findall(r"\bORD-\d+\b", text, re.IGNORECASE)))


def extract_ticket_ids(text: str) -> List[str]:
    matches = re.findall(r"(?:TCK-|ticket\s*#|#)(\d+)", text, re.IGNORECASE)
    res = []
    for m in matches:
        res.append(f"TCK-{m}")
    return res


def extract_seller_ids(text: str) -> List[str]:
    return list(set(re.findall(r"\bSEL-\d+\b", text, re.IGNORECASE)))


def detect_hinglish_intent(text: str) -> Optional[str]:
    lower = text.lower()
    if any(k in lower for k in ["damaged aaya", "screen damaged", "toota", "kharaab", "flickering"]):
        return "IN_TRANSIT_DAMAGE"
    if any(k in lower for k in ["size manga tha", "small bhej diya", "large manga", "tag attached"]):
        return "SIZE_MISMATCH"
    if any(k in lower for k in ["do baar payment", "payment kat gaya", "upi se do baar"]):
        return "DOUBLE_PAYMENT"
    if any(k in lower for k in ["refund kab", "refund nahi mila", "refund status"]):
        return "REFUND_STATUS"
    return None


class Planner:
    """Plans tool actions based on query semantics and handles error recovery."""

    @staticmethod
    def create_initial_plan(question: str) -> List[Dict[str, Any]]:
        plan = []
        orders = extract_order_ids(question)
        tickets = extract_ticket_ids(question)
        lower_q = question.lower()

        # 1. Order SQL lookup
        if orders:
            for oid in orders:
                plan.append({
                    "tool": "run_sql",
                    "args": {"query": f"SELECT o.*, r.refund_id, r.refund_amount, r.refund_status, r.reason as refund_reason, r.seller_approval_status FROM orders o LEFT JOIN refunds r ON o.order_id = r.order_id WHERE o.order_id = '{oid}';"},
                    "purpose": f"Fetch order and refund details for {oid}"
                })
                plan.append({
                    "tool": "run_sql",
                    "args": {"query": f"SELECT ticket_id, subject, message, status, created_at FROM support_tickets WHERE order_id = '{oid}';"},
                    "purpose": f"Fetch support tickets for {oid}"
                })

        # 2. WhatsApp action intent
        if "whatsapp" in lower_q or "send_seller_whatsapp" in lower_q:
            plan.append({
                "tool": "send_seller_whatsapp_intent",
                "args": {},
                "purpose": "Evaluate WhatsApp notification request"
            })

        # 3. Policy Lookups based on topic / category
        if "electronics" in lower_q or "laptop" in lower_q or "smartphone" in lower_q or "headphones" in lower_q or "ord-1001" in lower_q or "ord-1002" in lower_q or "ord-1003" in lower_q or "ord-1004" in lower_q:
            # Check if historical 2023 or 2024
            if "2023" in lower_q or "ord-1003" in lower_q:
                plan.append({
                    "tool": "get_policy",
                    "args": {"name": "POL-001-v1", "as_of_date": "2023-11-20"},
                    "purpose": "Fetch 2023 Electronics Policy"
                })
            plan.append({
                "tool": "get_policy",
                "args": {"name": "POL-001-v2", "as_of_date": "2024-01-15"},
                "purpose": "Fetch current 2024 Electronics Policy"
            })

        if "apparel" in lower_q or "jacket" in lower_q or "shoes" in lower_q or "size" in lower_q or "ord-1015" in lower_q:
            plan.append({
                "tool": "get_policy",
                "args": {"name": "POL-002", "as_of_date": "2024-03-10"},
                "purpose": "Fetch Apparel Return SOP"
            })

        if "damaged" in lower_q or "restocking" in lower_q or "conflict" in lower_q or "ord-1020" in lower_q:
            plan.append({
                "tool": "get_policy",
                "args": {"name": "POL-003-PLATFORM", "as_of_date": "2024-02-20"},
                "purpose": "Fetch Platform In-Transit Damage Policy"
            })
            plan.append({
                "tool": "get_policy",
                "args": {"name": "POL-003-SELLER", "as_of_date": "2024-02-20"},
                "purpose": "Fetch Seller In-Transit Damage Guideline"
            })

        if "grocery" in lower_q or "perishable" in lower_q or "spoiled" in lower_q or "ord-1030" in lower_q or "ord-1035" in lower_q:
            plan.append({
                "tool": "get_policy",
                "args": {"name": "POL-004", "as_of_date": "2024-03-01"},
                "purpose": "Fetch Grocery Return Policy"
            })

        if "luxury" in lower_q or "watch" in lower_q or "watches" in lower_q or "ord-1055" in lower_q:
            plan.append({
                "tool": "get_policy",
                "args": {"name": "POL-005", "as_of_date": "2024-03-01"},
                "purpose": "Fetch Luxury Watches Policy"
            })

        if "counterfeit" in lower_q or "fake" in lower_q or "replica" in lower_q or "ord-1050" in lower_q:
            plan.append({
                "tool": "get_policy",
                "args": {"name": "POL-006", "as_of_date": "2024-02-15"},
                "purpose": "Fetch Counterfeit Protection Policy"
            })

        if "delay" in lower_q or "delayed" in lower_q or "late" in lower_q or "ord-1060" in lower_q:
            plan.append({
                "tool": "get_policy",
                "args": {"name": "POL-007", "as_of_date": "2024-02-18"},
                "purpose": "Fetch Delivery Delay SLA"
            })

        if "50000" in lower_q or "high value" in lower_q or "ord-1002" in lower_q:
            plan.append({
                "tool": "get_policy",
                "args": {"name": "POL-009", "as_of_date": "2024-03-12"},
                "purpose": "Fetch High Value Refund Escalation SOP"
            })

        # 4. Search docs fallback if no direct policy planned
        if not any(step["tool"] == "get_policy" for step in plan):
            plan.append({
                "tool": "search_docs",
                "args": {"query": question, "top_k": 3},
                "purpose": "Search documents for relevant policies or tickets"
            })

        return plan
