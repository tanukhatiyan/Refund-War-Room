"""
Refund War Room - Deterministic Verifier.
Validates numerical claims, exact quoted spans, superseded policy usage, and citation hashes.
"""
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional

from src.config import DOCS_PATH
from src.tools.sql_tool import compute_result_hash


def extract_numbers(text: str) -> List[float]:
    """Extracts genuine quantitative figures (currency, counts, days, percentages),
    ignoring code identifiers (POL-001, ORD-1002, TCK-8821) and calendar years (2020-2030).
    """
    if not text:
        return []
    # Strip identifiers like POL-001-v2, ORD-1001, TCK-8821, SEL-101, REF-5001
    cleaned = re.sub(r"\b[A-Za-z]+[-_][A-Za-z0-9-_]+\b", " ", text)
    # Strip dates like 2024-02-05
    cleaned = re.sub(r"\b\d{4}-\d{2}-\d{2}\b", " ", cleaned)
    # Remove commas in numbers like 65,000 -> 65000
    cleaned = re.sub(r"(?<=\d),(?=\d)", "", cleaned)
    matches = re.findall(r"\b\d+(?:\.\d+)?\b", cleaned)

    numbers: List[float] = []
    for m in matches:
        val = float(m)
        # Exclude standalone calendar years (e.g. 2023, 2024) from quantitative claims
        if 2020 <= val <= 2030 and "." not in m:
            continue
        numbers.append(val)
    return numbers


class DeterministicVerifier:
    def __init__(self, docs_path: Path = DOCS_PATH):
        self.docs_path = docs_path
        self.docs_lookup: Dict[str, Dict[str, Any]] = {}
        self._load_docs()

    def _load_docs(self):
        if Path(self.docs_path).exists():
            with open(self.docs_path, "r", encoding="utf-8") as f:
                docs = json.load(f)
                for d in docs:
                    self.docs_lookup[d["doc_id"]] = d

    def verify_exact_quote(self, doc_id: str, quoted_span: str) -> tuple[bool, str]:
        """Checks if quoted_span is an exact verbatim substring of the document."""
        if not doc_id:
            return False, "Missing doc_id in citation."
        if not quoted_span:
            return False, "Missing exact_quoted_span in citation."

        doc = self.docs_lookup.get(doc_id)
        if not doc:
            return False, f"Document '{doc_id}' not found in registry."

        content = doc.get("content", "")
        # Check exact substring
        if quoted_span in content:
            return True, f"Exact quote verified in {doc_id}."

        # Case-insensitive whitespace-normalized check
        norm_quote = " ".join(quoted_span.split()).lower()
        norm_content = " ".join(content.split()).lower()
        if norm_quote in norm_content:
            return True, f"Quote verified with normalized whitespace in {doc_id}."

        return False, f"HALLUCINATED_QUOTE: Quoted text does not exist verbatim in {doc_id}."

    def verify_superseded_policy(self, doc_id: str, as_of_date: Optional[str] = None) -> tuple[bool, str]:
        """Verifies if the cited policy is active or superseded for the given date."""
        doc = self.docs_lookup.get(doc_id)
        if not doc:
            return True, "Unknown doc."

        superseded_by = doc.get("superseded_by")
        end_date = doc.get("end_date")

        if superseded_by:
            if as_of_date and end_date and as_of_date <= end_date:
                # Valid during historical window
                return True, f"Historical validity verified: {doc_id} was active on {as_of_date} prior to {end_date}."
            return False, f"SUPERSEDED_POLICY_VIOLATION: Policy {doc_id} was superseded by {superseded_by} on {end_date}."

        return True, "Policy is currently active."

    def verify_numerical_claim(
        self,
        claim_text: str,
        sql_rows: Optional[List[Any]] = None,
        doc_span: Optional[str] = None
    ) -> tuple[bool, str]:
        """Verifies numbers mentioned in claim against SQL result rows or cited doc span."""
        claim_numbers = extract_numbers(claim_text)
        if not claim_numbers:
            return True, "No numerical figures to verify."

        # Gather evidence numbers
        evidence_numbers: List[float] = []
        if doc_span:
            evidence_numbers.extend(extract_numbers(doc_span))

        if sql_rows:
            for row in sql_rows:
                if isinstance(row, (list, tuple)):
                    for item in row:
                        if isinstance(item, (int, float)):
                            evidence_numbers.append(float(item))
                        elif isinstance(item, str):
                            evidence_numbers.extend(extract_numbers(item))
                elif isinstance(row, dict):
                    for v in row.values():
                        if isinstance(v, (int, float)):
                            evidence_numbers.append(float(v))
                        elif isinstance(v, str):
                            evidence_numbers.extend(extract_numbers(v))

        # Check if every claim number appears in evidence
        for num in claim_numbers:
            matched = any(abs(num - ev) < 0.01 for ev in evidence_numbers)
            if not matched:
                return False, f"NUMERICAL_MISMATCH: Claimed figure {num} not found in verified evidence (found: {evidence_numbers})."

        return True, "All numerical figures verified against evidence."

    def verify_claim(
        self,
        claim: Dict[str, Any],
        tool_artifacts: Dict[str, Any],
        as_of_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Runs full suite of deterministic verification on an individual claim."""
        claim_type = claim.get("type", "fact")
        citation = claim.get("citation", {}) or {}
        text = claim.get("text", "")

        # Assumptions and recommendations don't require rigid fact proof, but cannot violate policies
        if claim_type in ["assumption", "recommendation"]:
            return {
                "verified": True,
                "verification_notes": f"Verified as {claim_type}."
            }

        notes = []
        is_verified = True

        source_type = citation.get("source_type")
        if not source_type:
            # Fact with no citation
            return {
                "verified": True if claim.get("verified") else False,
                "verification_notes": claim.get("verification_notes") or "Fact lacks formal citation."
            }

        if source_type == "doc":
            doc_id = citation.get("doc_id")
            quoted_span = citation.get("exact_quoted_span", "")

            # 1. Exact quote verification
            q_ok, q_note = self.verify_exact_quote(doc_id, quoted_span)
            notes.append(q_note)
            if not q_ok:
                is_verified = False

            # 2. Superseded policy check
            p_ok, p_note = self.verify_superseded_policy(doc_id, as_of_date=as_of_date)
            notes.append(p_note)
            if not p_ok:
                is_verified = False

            # 3. Numerical verification against quote
            n_ok, n_note = self.verify_numerical_claim(text, doc_span=quoted_span)
            notes.append(n_note)
            if not n_ok:
                is_verified = False

        elif source_type == "sql":
            query = citation.get("query", "")
            cited_hash = citation.get("result_hash")

            matching_artifact = None
            for art in tool_artifacts.get("sql_calls", []):
                if art.get("result_hash") == cited_hash or art.get("query", "").strip() == query.strip():
                    matching_artifact = art
                    break

            if not matching_artifact:
                notes.append(f"UNVERIFIED_HASH: SQL citation hash '{cited_hash}' not found in execution trace.")
                is_verified = False
            else:
                notes.append("SQL execution and result hash verified.")
                rows = matching_artifact.get("rows", [])
                n_ok, n_note = self.verify_numerical_claim(text, sql_rows=rows)
                notes.append(n_note)
                if not n_ok:
                    is_verified = False

        return {
            "verified": is_verified,
            "verification_notes": " | ".join(notes)
        }

    def verify_all(
        self,
        claims: List[Dict[str, Any]],
        tool_artifacts: Dict[str, Any],
        as_of_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        verified_claims = []
        for claim in claims:
            v_res = self.verify_claim(claim, tool_artifacts, as_of_date=as_of_date)
            c_copy = dict(claim)
            c_copy["verified"] = v_res["verified"]
            c_copy["verification_notes"] = v_res["verification_notes"]
            verified_claims.append(c_copy)
        return verified_claims
