"""
Unit tests for Evaluation Suite.
"""
from src.evaluation.eval_suite import EVALUATION_QUESTIONS
from src.evaluation.eval_runner import evaluate_single_case, run_evaluation_benchmark


def test_eval_questions_count():
    assert len(EVALUATION_QUESTIONS) == 12


def test_single_case_evaluation():
    q1 = EVALUATION_QUESTIONS[0]
    res_on = evaluate_single_case(q1, verifier_enabled=True)
    assert res_on["id"] == "Q1"
    assert res_on["tool_calls"] <= 8
    assert res_on["termination_ok"] is True


def test_full_benchmark_smoke():
    benchmark_data = run_evaluation_benchmark()
    assert "summary_verifier_enabled" in benchmark_data
    assert "summary_verifier_disabled" in benchmark_data
    assert benchmark_data["summary_verifier_enabled"]["total_cases"] == 12
