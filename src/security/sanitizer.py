"""
Refund War Room - Data Sanitizer & Untrusted Data Tainting.
"""
from typing import Dict, Any, List


def taint_data(data: Any, source_name: str) -> Dict[str, Any]:
    """Wraps external data in an untrusted data container."""
    return {
        "tainted": True,
        "source": source_name,
        "is_executable_instruction": False,
        "data": data
    }


def clean_output_text(text: str) -> str:
    """Removes potential terminal control sequences or HTML injection tags."""
    if not isinstance(text, str):
        return text
    cleaned = text.replace("<script>", "").replace("</script>", "")
    cleaned = cleaned.replace("javascript:", "")
    return cleaned
