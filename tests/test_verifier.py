"""
Unit tests for Deterministic Verifier and Conflict Resolver.
"""
from src.verifier.verifier import DeterministicVerifier, extract_numbers
from src.verifier.conflict_resolver import resolve_policy_conflict


def test_extract_numbers():
    text = "Order ORD-1001 was delivered on 2024-02-05 with amount INR 64,999.50 and 7 days return window under POL-001-v2."
    nums = extract_numbers(text)
    assert 64999.5 in nums
    assert 7.0 in nums
    # Alphanumeric codes and calendar year 2024 should not be in quantitative numbers
    assert 1001.0 not in nums
    assert 1.0 not in nums
    assert 2024.0 not in nums


def test_verify_exact_quote():
    verifier = DeterministicVerifier()
    # Exact quote present in POL-001-v2
    ok, note = verifier.verify_exact_quote(
        "POL-001-v2",
        "Opened electronics are eligible for replacement only within 7 days of delivery if verified defective."
    )
    assert ok is True

    # Hallucinated quote
    ok, note = verifier.verify_exact_quote(
        "POL-001-v2",
        "Customers get free unlimited cash refunds forever."
    )
    assert ok is False
    assert "HALLUCINATED_QUOTE" in note


def test_verify_superseded_policy():
    verifier = DeterministicVerifier()
    # In 2023, POL-001-v1 was valid
    ok, note = verifier.verify_superseded_policy("POL-001-v1", as_of_date="2023-11-15")
    assert ok is True

    # In 2024, POL-001-v1 was superseded by POL-001-v2
    ok, note = verifier.verify_superseded_policy("POL-001-v1", as_of_date="2024-01-15")
    assert ok is False
    assert "SUPERSEDED_POLICY_VIOLATION" in note


def test_conflict_resolution_authority():
    # Platform Policy (rank 80) vs Seller Guideline (rank 20)
    policy_a = {"doc_id": "POL-003-PLATFORM", "authority": "Platform Policy", "source_rank": 80, "effective_date": "2024-02-01"}
    policy_b = {"doc_id": "POL-003-SELLER", "authority": "Seller Guidelines", "source_rank": 20, "effective_date": "2024-02-15"}

    res = resolve_policy_conflict(policy_a, policy_b)
    assert res["resolved"] is True
    assert res["winner"] == "POL-003-PLATFORM"
    assert res["loser"] == "POL-003-SELLER"
    assert res["rule"] == "SOURCE_AUTHORITY_HIERARCHY"


def test_conflict_resolution_superseded():
    policy_old = {"doc_id": "POL-001-v1", "superseded_by": "POL-001-v2", "authority": "Platform Policy"}
    policy_new = {"doc_id": "POL-001-v2", "superseded_by": None, "authority": "Legal/Executive Policy"}

    res = resolve_policy_conflict(policy_old, policy_new)
    assert res["resolved"] is True
    assert res["winner"] == "POL-001-v2"
    assert res["rule"] == "SUPERSEDED_REVISION"
