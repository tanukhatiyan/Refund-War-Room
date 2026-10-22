"""
Refund War Room - FastAPI Backend Service.
Exposes endpoints for querying the state-machine agent, running evaluations,
inspecting policies, and reviewing WhatsApp security audit logs.
"""
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from src.agent.models import AgentResponse
from src.agent.state_machine import StateMachineAgent
from src.evaluation.eval_runner import run_evaluation_benchmark
from src.data.documents import DOCUMENTS
from src.config import DB_PATH, AUDIT_LOG_PATH
import sqlite3

app = FastAPI(
    title="Refund War Room API",
    description="Deterministic State-Machine Agent with Structured Citations, Policy Conflict Resolution, and Verifier",
    version="1.0.0"
)


class QueryRequest(BaseModel):
    question: str = Field(..., description="User query about order, refund, policy, or ticket")
    verifier_enabled: bool = Field(default=True, description="Enable deterministic verification engine")
    failure_wrapper_enabled: bool = Field(default=False, description="Enable 15% transient failure injection")
    failure_rate: float = Field(default=0.15, ge=0.0, le=1.0)
    is_user_confirmed: bool = Field(default=False, description="Explicit user confirmation for actions")
    origin: str = Field(default="user", description="Origin of request ('user' vs 'document')")


@app.get("/health")
def health_check():
    db_ok = False
    order_count = 0
    try:
        if DB_PATH.exists():
            conn = sqlite3.connect(str(DB_PATH))
            cur = conn.cursor()
            cur.execute("SELECT count(*) FROM orders")
            order_count = cur.fetchone()[0]
            conn.close()
            db_ok = True
    except Exception as e:
        db_ok = False

    return {
        "status": "healthy" if db_ok else "degraded",
        "database_connected": db_ok,
        "database_path": str(DB_PATH),
        "total_orders_in_db": order_count,
        "total_documents_registered": len(DOCUMENTS),
        "version": "1.0.0"
    }


@app.post("/query", response_model=AgentResponse)
def query_agent(request: QueryRequest):
    try:
        agent = StateMachineAgent(
            verifier_enabled=request.verifier_enabled,
            failure_wrapper_enabled=request.failure_wrapper_enabled,
            failure_rate=request.failure_rate
        )
        response = agent.execute(
            question=request.question,
            is_user_confirmed=request.is_user_confirmed,
            origin=request.origin
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent execution failed: {str(e)}")


@app.post("/evaluate")
def run_evaluation():
    try:
        results = run_evaluation_benchmark()
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")


@app.get("/policies")
def list_policies():
    return {
        "count": len(DOCUMENTS),
        "policies": DOCUMENTS
    }


@app.get("/audit-log")
def get_audit_log(limit: int = 50):
    lines = []
    if AUDIT_LOG_PATH.exists():
        with open(AUDIT_LOG_PATH, "r", encoding="utf-8") as f:
            all_lines = f.readlines()
            lines = [line.strip() for line in all_lines[-limit:]]
    return {
        "count": len(lines),
        "entries": lines
    }
