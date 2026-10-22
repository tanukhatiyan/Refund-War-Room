"""
Refund War Room - Simulated WhatsApp Tool with Security Gating.
Enforces allow-list, argument validation, explicit user confirmation, and injection blocking.
"""
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from src.config import (
    ALLOWLISTED_SELLERS,
    ALLOWLISTED_PHONES,
    PROMPT_INJECTION_PATTERNS,
    AUDIT_LOG_PATH
)


def log_whatsapp_event(event_type: str, details: Dict[str, Any], log_path: Path = AUDIT_LOG_PATH):
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "event_type": event_type,
        "details": details
    }
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"{entry}\n")


def send_seller_whatsapp(
    seller_id: str,
    phone: str,
    message: str,
    is_user_confirmed: bool = False,
    origin: str = "user",
    log_path: Path = AUDIT_LOG_PATH
) -> Dict[str, Any]:
    """Simulated WhatsApp dispatch with security gating:
    - User origin confirmation
    - Verified seller allow-list
    - Phone number validation & matching
    - Prompt injection payload scanning
    """
    clean_seller_id = seller_id.strip().upper()
    clean_phone = phone.strip()
    clean_message = message.strip()

    # Gate 1: Check origin (Reject document-instructed actions)
    if origin.lower() != "user":
        reason = "SECURITY_VIOLATION: Automated action attempted from untrusted source or document instructions."
        log_whatsapp_event("BLOCKED_UNTRUSTED_ORIGIN", {
            "seller_id": clean_seller_id, "phone": clean_phone, "origin": origin, "reason": reason
        }, log_path)
        return {
            "status": "blocked",
            "code": "UNTRUSTED_ORIGIN",
            "error": reason
        }

    # Gate 2: Explicit User Confirmation
    if not is_user_confirmed:
        reason = "ACTION_GATED: Explicit user-origin confirmation required before dispatching external WhatsApp alert."
        log_whatsapp_event("BLOCKED_UNCONFIRMED", {
            "seller_id": clean_seller_id, "phone": clean_phone, "reason": reason
        }, log_path)
        return {
            "status": "blocked",
            "code": "CONFIRMATION_REQUIRED",
            "error": reason
        }

    # Gate 3: Allow-listed Seller ID
    if clean_seller_id not in ALLOWLISTED_SELLERS:
        reason = f"SECURITY_VIOLATION: Seller ID '{clean_seller_id}' is not in verified seller allow-list."
        log_whatsapp_event("BLOCKED_UNAUTHORIZED_SELLER", {
            "seller_id": clean_seller_id, "phone": clean_phone, "reason": reason
        }, log_path)
        return {
            "status": "blocked",
            "code": "UNAUTHORIZED_SELLER",
            "error": reason
        }

    # Gate 4: Allow-listed and Matched Phone
    expected_phone = ALLOWLISTED_SELLERS[clean_seller_id]["phone"]
    if clean_phone != expected_phone or clean_phone not in ALLOWLISTED_PHONES:
        reason = f"SECURITY_VIOLATION: Phone number '{clean_phone}' does not match registered allow-listed number '{expected_phone}' for seller '{clean_seller_id}'."
        log_whatsapp_event("BLOCKED_PHONE_MISMATCH", {
            "seller_id": clean_seller_id, "phone": clean_phone, "expected_phone": expected_phone, "reason": reason
        }, log_path)
        return {
            "status": "blocked",
            "code": "PHONE_MISMATCH",
            "error": reason
        }

    # Gate 5: Argument & Payload Injection Check
    for pattern in PROMPT_INJECTION_PATTERNS:
        if re.search(pattern, clean_message, re.IGNORECASE):
            reason = f"SECURITY_VIOLATION: WhatsApp message contains prohibited prompt-injection pattern '{pattern}'."
            log_whatsapp_event("BLOCKED_INJECTION_PAYLOAD", {
                "seller_id": clean_seller_id, "phone": clean_phone, "pattern": pattern, "reason": reason
            }, log_path)
            return {
                "status": "blocked",
                "code": "INJECTION_DETECTED",
                "error": reason
            }

    # Gate 6: Basic Phone Regex Validation
    if not re.match(r"^\+?[0-9\-\s]{8,20}$", clean_phone):
        reason = "INVALID_ARGUMENT: Invalid phone number format."
        log_whatsapp_event("BLOCKED_INVALID_PHONE_FORMAT", {
            "seller_id": clean_seller_id, "phone": clean_phone, "reason": reason
        }, log_path)
        return {
            "status": "blocked",
            "code": "INVALID_FORMAT",
            "error": reason
        }

    # All gates passed: simulate logging
    delivery_record = {
        "status": "delivered_simulated",
        "seller_id": clean_seller_id,
        "seller_name": ALLOWLISTED_SELLERS[clean_seller_id]["name"],
        "phone": clean_phone,
        "message": clean_message,
        "timestamp": datetime.utcnow().isoformat()
    }
    log_whatsapp_event("DELIVERED_SIMULATED", delivery_record, log_path)

    return {
        "status": "success",
        "action": "send_seller_whatsapp",
        "delivery": delivery_record
    }
