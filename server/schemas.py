# Author: 晨星
"""API request/response schemas. Uniform envelope: {code, data, message}."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class Envelope(BaseModel):
    code: int = 0
    data: Any = None
    message: str = "ok"


class DocumentIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=1, max_length=2_000_000)


class DocumentOut(BaseModel):
    doc_id: str
    title: str
    chunks: int


class QueryIn(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    top_k: int = Field(default=5, ge=1, le=20)
    mode: Literal["hybrid", "dense", "bm25"] = "hybrid"
    stream: bool = False


class CitationOut(BaseModel):
    chunk_id: str
    doc_id: str
    snippet: str
    score: float


class QueryOut(BaseModel):
    question: str
    answer: str
    provider: str
    retrieval_mode: str
    citations: list[CitationOut]


class AgentIn(BaseModel):
    question: str = Field(min_length=1, max_length=4000)


class AgentStepOut(BaseModel):
    thought: str
    action: str
    action_input: str
    observation: str


class AgentOut(BaseModel):
    question: str
    answer: str
    steps: list[AgentStepOut]
    tool_calls: int


class EvalIn(BaseModel):
    top_k: int = Field(default=3, ge=1, le=10)


class StatsOut(BaseModel):
    documents: int
    chunks: int
