# Author: 晨星
"""WorldAI core data models. Pure data, zero logic."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Document:
    """An ingested source document."""

    id: str
    title: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Chunk:
    """A retrievable text unit produced from a Document."""

    id: str
    doc_id: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchHit:
    """One retrieval result."""

    chunk: Chunk
    score: float
    source: str  # "vector" | "bm25" | "fusion" | "rerank"


@dataclass
class Citation:
    """A cited chunk inside an answer."""

    chunk_id: str
    doc_id: str
    snippet: str
    score: float


@dataclass
class QueryAnswer:
    """RAG query result."""

    question: str
    answer: str
    citations: list[Citation]
    provider: str
    retrieval_mode: str


@dataclass
class AgentStep:
    """One step of an agent trajectory."""

    thought: str
    action: str
    action_input: str
    observation: str


@dataclass
class AgentResult:
    """Agent run output."""

    question: str
    answer: str
    steps: list[AgentStep]
    tool_calls: int
