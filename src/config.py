"""
Refund War Room - Global Configuration and Constants.
"""
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "refunds.db"
DOCS_PATH = DATA_DIR / "documents.json"
AUDIT_LOG_PATH = DATA_DIR / "whatsapp_audit.log"

# Agent Constants
MAX_TOOL_CALLS = 8
DEFAULT_FAILURE_RATE = 0.15

# Source Authority Hierarchy for deterministic conflict resolution
AUTHORITY_HIERARCHY = {
    "Legal/Executive Policy": 100,
    "Platform Policy": 80,
    "Standard Operating Procedure": 60,
    "Customer Support Guidelines": 40,
    "Seller Guidelines": 20,
    "FAQ": 10,
    "Community Post": 5,
}

# Gating & Security Allow-list
ALLOWLISTED_SELLERS = {
    "SEL-101": {"name": "Apex Electronics Ltd", "phone": "+91-9876543210", "verified": True},
    "SEL-102": {"name": "StyleHub Apparel", "phone": "+91-9876543211", "verified": True},
    "SEL-103": {"name": "FreshFarm Grocers", "phone": "+91-9876543212", "verified": True},
    "SEL-104": {"name": "Timeless Watches Co", "phone": "+91-9876543213", "verified": True},
    "SEL-105": {"name": "GlowBeauty Essentials", "phone": "+91-9876543214", "verified": True},
    "SEL-106": {"name": "Nordic Furniture House", "phone": "+91-9876543215", "verified": True},
}

ALLOWLISTED_PHONES = {info["phone"] for info in ALLOWLISTED_SELLERS.values()}

# Known Prompt Injection Signatures
PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions",
    r"system\s+override",
    r"security\s+override",
    r"disregard\s+(all\s+)?guidelines",
    r"execute\s+send_seller_whatsapp",
    r"unconditional\s+(cash\s+)?refund",
    r"do\s+not\s+consult\s+sql",
    r"bypass\s+(all\s+)?verification",
]
