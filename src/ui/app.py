"""
Refund War Room - Streamlit Interactive UI.
Displays questions, answers, claim tags, exact citations, policy conflict resolutions,
state-machine execution timeline, and live evaluation benchmark.
"""
import streamlit as st
import json
import pandas as pd
from typing import Dict, Any

from src.agent.state_machine import StateMachineAgent
from src.evaluation.eval_suite import EVALUATION_QUESTIONS
from src.evaluation.eval_runner import run_evaluation_benchmark
from src.config import ALLOWLISTED_SELLERS, AUDIT_LOG_PATH

st.set_page_config(
    page_title="Refund War Room",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🛡️ Refund War Room")
st.caption("AI Engineering Challenge: Deterministic State-Machine Agent, Verifier, Citations & Security Guardrails")

# -----------------------------------------------------------------------------
# SIDEBAR CONTROLS
# -----------------------------------------------------------------------------
st.sidebar.header("Agent Controls")

preset_options = ["(Custom Question)"] + [f"{q['id']}: {q['category']} - {q['question'][:50]}..." for q in EVALUATION_QUESTIONS]
selected_preset = st.sidebar.selectbox("Load Evaluation Question Preset", preset_options)

verifier_enabled = st.sidebar.checkbox("Deterministic Verifier", value=True, help="Validates numerical values, exact quotes, and flags superseded policies.")
failure_enabled = st.sidebar.checkbox("15% Failure Wrapper (Chaos)", value=False, help="Injects ~15% simulated timeouts, errors, and empty results.")
user_confirmed = st.sidebar.checkbox("User Action Confirmation", value=False, help="Simulate explicit user confirmation required for external WhatsApp actions.")

st.sidebar.markdown("---")
st.sidebar.subheader("System Allow-list")
with st.sidebar.expander("Verified Sellers"):
    for sid, sdata in ALLOWLISTED_SELLERS.items():
        st.markdown(f"- **{sid}**: {sdata['name']} (`{sdata['phone']}`)")

# -----------------------------------------------------------------------------
# QUESTION INPUT
# -----------------------------------------------------------------------------
default_q = ""
if selected_preset != "(Custom Question)":
    qid = selected_preset.split(":")[0]
    matched_q = next((q for q in EVALUATION_QUESTIONS if q["id"] == qid), None)
    if matched_q:
        default_q = matched_q["question"]

question_input = st.text_area(
    "Enter Customer Query, Support Ticket, or Investigation Request:",
    value=default_q or "Customer with order ORD-1001 (OnePlus 12 5G) received the item on 2024-02-05, opened the box, found it defective, and is demanding a cash refund on 2024-02-09 (4 days later). What is their eligibility under current electronics policy?",
    height=110
)

col_run, col_eval = st.columns([1, 4])
with col_run:
    run_btn = st.button("🚀 Run Agent Investigation", type="primary", use_container_width=True)

# -----------------------------------------------------------------------------
# AGENT EXECUTION
# -----------------------------------------------------------------------------
if run_btn and question_input.strip():
    with st.spinner("Executing State-Machine (Plan -> Act -> Observe -> Verify -> Decide)..."):
        agent = StateMachineAgent(
            verifier_enabled=verifier_enabled,
            failure_wrapper_enabled=failure_enabled,
            failure_rate=0.15,
            failure_seed=42
        )
        response = agent.execute(
            question=question_input.strip(),
            is_user_confirmed=user_confirmed,
            origin="user"
        )
        st.session_state["last_response"] = response

if "last_response" in st.session_state:
    resp = st.session_state["last_response"]

    # Header Decision Banner
    st.markdown("### Agent Investigation Result")
    if resp.decision == "ANSWER":
        st.success(f"**DECISION: ANSWER** | Tool Calls: {resp.tool_calls_count}/8 | Verifier: {'ACTIVE' if resp.verifier_enabled else 'DISABLED'}")
    else:
        st.warning(f"**DECISION: ABSTAIN** | Tool Calls: {resp.tool_calls_count}/8 | Verifier: {'ACTIVE' if resp.verifier_enabled else 'DISABLED'}")
        if resp.abstain_reason:
            st.info(f"**Abstention Reason:** {resp.abstain_reason}")

    # Tabs
    tab_ans, tab_claims, tab_conflicts, tab_trace, tab_security = st.tabs([
        "📋 Answer & Synthesis",
        "🏷️ Structured Claims & Citations",
        "⚖️ Policy Conflicts & Resolutions",
        "🔄 State Machine & Tool Trace",
        "🔒 Security & WhatsApp Audit"
    ])

    with tab_ans:
        st.markdown("#### Synthesized Response")
        st.code(resp.answer_text, language="text")

        if resp.missing_evidence:
            st.markdown("#### ⚠️ Missing Evidence Identified:")
            for me in resp.missing_evidence:
                st.markdown(f"- 🔴 {me}")

    with tab_claims:
        st.markdown("#### Granular Claim Breakdown")
        if not resp.claims:
            st.info("No explicit claims extracted.")
        else:
            for i, c in enumerate(resp.claims, 1):
                type_colors = {
                    "fact": "blue",
                    "assumption": "purple",
                    "recommendation": "green"
                }
                c_color = type_colors.get(c.type, "grey")
                v_badge = "✅ Verified" if c.verified else "❌ Unverified"
                
                with st.expander(f"Claim #{i} [{c.type.upper()}] - {v_badge}: {c.text[:70]}..."):
                    st.markdown(f"**Claim Text:** {c.text}")
                    st.markdown(f"**Type:** :{c_color}[{c.type.upper()}] | **Status:** {v_badge}")
                    if c.verification_notes:
                        st.caption(f"**Verification Notes:** {c.verification_notes}")

                    if c.citation:
                        st.markdown("**Citation:**")
                        if c.citation.source_type == "sql":
                            st.markdown(f"- **Source:** SQL Database")
                            st.code(c.citation.query, language="sql")
                            st.caption(f"Result SHA-256 Hash: `{c.citation.result_hash}`")
                        elif c.citation.source_type == "doc":
                            st.markdown(f"- **Document ID:** `{c.citation.doc_id}`")
                            st.markdown(f"- **Exact Quoted Span:**")
                            st.info(f'"{c.citation.exact_quoted_span}"')

    with tab_conflicts:
        st.markdown("#### Policy Conflicts & Authority Resolution")
        if not resp.conflicts:
            st.info("No policy conflicts identified for this query.")
        else:
            for conf in resp.conflicts:
                st.markdown(f"**Conflict Detected:** `{conf.policy_a}` vs `{conf.policy_b}`")
                st.markdown(f"- **Winner:** `{conf.winner}`")
                st.markdown(f"- **Loser:** `{conf.loser}`")
                st.markdown(f"- **Resolution Rule Applied:** `{conf.rule}`")
                st.caption(f"**Details:** {conf.explanation}")

    with tab_trace:
        st.markdown("#### State Transitions")
        st.markdown(" ➔ ".join([f"`{s}`" for s in resp.state_history]))

        st.markdown("#### Tool Execution Timeline")
        trace_data = []
        for t in resp.execution_trace:
            trace_data.append({
                "Call #": t.call_index,
                "Tool": t.tool_name,
                "Status": t.status,
                "Result Preview": t.result_preview,
                "Result Hash": t.result_hash or "N/A",
                "Failure Mode": t.failure_mode or "None"
            })
        st.dataframe(pd.DataFrame(trace_data), use_container_width=True)

    with tab_security:
        st.markdown("#### Security & Injection Guardrails")
        if resp.prompt_injection_detected:
            st.error("🚨 Prompt Injection Signatures Detected! Untrusted directives quarantined.")
        else:
            st.success("✅ Clean query. No prompt injection patterns detected.")

        st.markdown("#### WhatsApp Security Audit Log")
        if AUDIT_LOG_PATH.exists():
            with open(AUDIT_LOG_PATH, "r", encoding="utf-8") as f:
                logs = f.readlines()
                if logs:
                    st.code("".join(logs[-10:]), language="json")
                else:
                    st.info("Audit log is currently empty.")
        else:
            st.info("Audit log is clean.")

# -----------------------------------------------------------------------------
# BENCHMARK EVALUATION SECTION
# -----------------------------------------------------------------------------
st.markdown("---")
st.subheader("📊 Evaluation Benchmark Suite (12 Questions)")
st.caption("Runs reproducible head-to-head comparison: Deterministic Verifier ON vs OFF.")

if st.button("⚡ Run Full 12-Question Benchmark"):
    with st.spinner("Running 12 test questions across both configurations..."):
        benchmark_results = run_evaluation_benchmark()
        s_on = benchmark_results["summary_verifier_enabled"]
        s_off = benchmark_results["summary_verifier_disabled"]

        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        m_col1.metric("Verifier ON Pass Rate", f"{s_on['pass_rate_pct']}%", f"+{round(s_on['pass_rate_pct'] - s_off['pass_rate_pct'], 1)}%")
        m_col2.metric("Verifier ON Decision Accuracy", f"{s_on['decision_accuracy_pct']}%")
        m_col3.metric("Termination Guarantee", f"{s_on['termination_guarantee_pct']}%")
        m_col4.metric("Security Defense Rate", f"{s_on['security_defense_rate_pct']}%")

        st.markdown("##### Detailed Head-to-Head Comparison")
        comp_rows = []
        for on_c, off_c in zip(benchmark_results["details_verifier_enabled"], benchmark_results["details_verifier_disabled"]):
            comp_rows.append({
                "ID": on_c["id"],
                "Category": on_c["category"],
                "Expected": on_c["expected_decision"],
                "Verifier ON": on_c["actual_decision"],
                "Verifier OFF": off_c["actual_decision"],
                "ON Passed": "✅" if on_c["passed"] else "❌",
                "OFF Passed": "✅" if off_c["passed"] else "❌",
                "Tool Calls": on_c["tool_calls"]
            })
        st.dataframe(pd.DataFrame(comp_rows), use_container_width=True)
