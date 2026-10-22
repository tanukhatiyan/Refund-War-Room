"""
Unit tests for State-Machine Agent Lifecycle and Termination Guarantees.
"""
from src.agent.state_machine import StateMachineAgent


def test_state_machine_lifecycle():
    agent = StateMachineAgent(verifier_enabled=True)
    resp = agent.execute("What is the order amount and status for order ORD-1001?")
    
    assert "PLAN" in resp.state_history
    assert any("ACT:" in s for s in resp.state_history)
    assert any("OBSERVE:" in s for s in resp.state_history)
    assert "VERIFY" in resp.state_history
    assert resp.decision in ["ANSWER", "ABSTAIN"]
    assert resp.tool_calls_count <= 8


def test_tool_call_limit_guaranteed_termination():
    agent = StateMachineAgent(verifier_enabled=True)
    # Query with many order IDs that could theoretically trigger unbounded tool calls
    query = "Check orders ORD-1001, ORD-1002, ORD-1003, ORD-1004, ORD-1015, ORD-1020, ORD-1030, ORD-1035, ORD-1050, ORD-1055, ORD-1060."
    resp = agent.execute(query)

    assert resp.tool_calls_count <= 8
    assert resp.decision in ["ANSWER", "ABSTAIN"]


def test_unanswerable_missing_order_abstains():
    agent = StateMachineAgent(verifier_enabled=True)
    resp = agent.execute("What is the refund status for order ORD-9999?")

    assert resp.decision == "ABSTAIN"
    assert any("ORD-9999" in me for me in resp.missing_evidence)


def test_claims_structured_citations():
    agent = StateMachineAgent(verifier_enabled=True)
    resp = agent.execute("Review order ORD-1001 eligibility under current electronics policy.")
    
    assert len(resp.claims) > 0
    fact_claims = [c for c in resp.claims if c.type == "fact"]
    assert len(fact_claims) > 0
    for fc in fact_claims:
        if fc.citation:
            assert fc.citation.source_type in ["sql", "doc"]
