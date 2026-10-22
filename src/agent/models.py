"""
Refund War Room - Data Models & Pydantic Schemas.
"""
from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field


class Citation(BaseModel):
    source_type: Literal["sql", "doc"]
    # For SQL citations:
    query: Optional[str] = None
    result_hash: Optional[str] = None
    # For Doc citations:
    doc_id: Optional[str] = None
    exact_quoted_span: Optional[str] = None


class Claim(BaseModel):
    text: str
    type: Literal["fact", "assumption", "recommendation"]
    citation: Optional[Citation] = None
    verified: bool = False
    verification_notes: Optional[str] = None


class ConflictResolution(BaseModel):
    policy_a: str
    policy_b: str
    winner: Optional[str] = None
    loser: Optional[str] = None
    rule: str
    explanation: str


class ToolExecutionTrace(BaseModel):
    call_index: int
    tool_name: str
    arguments: Dict[str, Any]
    status: str
    result_preview: str
    result_hash: Optional[str] = None
    failure_mode: Optional[str] = None


class AgentResponse(BaseModel):
    question: str
    decision: Literal["ANSWER", "ABSTAIN"]
    abstain_reason: Optional[str] = None
    answer_text: str
    claims: List[Claim] = Field(default_factory=list)
    conflicts: List[ConflictResolution] = Field(default_factory=list)
    missing_evidence: List[str] = Field(default_factory=list)
    tool_calls_count: int = 0
    state_history: List[str] = Field(default_factory=list)
    execution_trace: List[ToolExecutionTrace] = Field(default_factory=list)
    verifier_enabled: bool = True
    prompt_injection_detected: bool = False
