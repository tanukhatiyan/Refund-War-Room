"""
Refund War Room - Security Guardrails & Prompt Injection Defense.
Treats retrieved documents as untrusted data, detects prompt injections, and guards actions.
"""
import re
from typing import Dict, Any, List, Tuple
from src.config import PROMPT_INJECTION_PATTERNS, ALLOWLISTED_SELLERS, ALLOWLISTED_PHONES


def detect_prompt_injection(text: str) -> Dict[str, Any]:
    """Scans text for prompt injection patterns, override instructions, and jailbreak signatures."""
    if not text:
        return {"detected": False, "matches": [], "risk_score": 0.0}

    matched_patterns = []
    for pattern in PROMPT_INJECTION_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            matched_patterns.append(pattern)

    risk_score = min(1.0, len(matched_patterns) * 0.4)
    return {
        "detected": len(matched_patterns) > 0,
        "matches": matched_patterns,
        "risk_score": round(risk_score, 2),
        "alert": "PROMPT_INJECTION_ATTEMPT_DETECTED" if matched_patterns else "CLEAN"
    }


def is_indirect_injection_attempt(text: str) -> bool:
    """Checks if a document contains instructions attempting to hijack agent behavior."""
    detection = detect_prompt_injection(text)
    return detection["detected"]


def validate_whatsapp_request(
    seller_id: str,
    phone: str,
    message: str,
    is_user_confirmed: bool,
    origin: str
) -> Tuple[bool, str]:
    """Validates that a WhatsApp dispatch request meets all security constraints."""
    if origin.lower() != "user":
        return False, "DENIED: Action origin is untrusted (originated from document or indirect instruction)."

    if not is_user_confirmed:
        return False, "DENIED: Explicit user confirmation required for external communication."

    clean_id = seller_id.strip().upper()
    if clean_id not in ALLOWLISTED_SELLERS:
        return False, f"DENIED: Seller '{clean_id}' is not in the verified allowlist."

    clean_phone = phone.strip()
    expected_phone = ALLOWLISTED_SELLERS[clean_id]["phone"]
    if clean_phone != expected_phone or clean_phone not in ALLOWLISTED_PHONES:
        return False, f"DENIED: Phone '{clean_phone}' does not match registered allowlist for seller '{clean_id}'."

    injection_check = detect_prompt_injection(message)
    if injection_check["detected"]:
        return False, f"DENIED: Message body contains prompt injection signatures: {injection_check['matches']}."

    return True, "PASSED"
