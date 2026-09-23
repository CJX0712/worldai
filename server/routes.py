# Author: 晨星
"""API route handlers under /api/v1. Business logic lives in core/."""
from __future__ import annotations

import json
from collections.abc import Iterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from core.agent import Agent
from core.pipeline import RAGPipeline
from eval.runner import default_golden_set, run_eval

from .schemas import (
    AgentIn,
    AgentOut,
    AgentStepOut,
    CitationOut,
    DocumentIn,
    DocumentOut,
    Envelope,
    EvalIn,
    QueryIn,
    QueryOut,
    StatsOut,
)

router = APIRouter(prefix="/api/v1")

# Injected by server.app.create_app via router attributes.
_pipeline: RAGPipeline
_agent: Agent


def bind(pipeline: RAGPipeline, agent: Agent) -> None:
    global _pipeline, _agent
    _pipeline = pipeline
    _agent = agent


def _env(data: object, message: str = "ok", code: int = 0) -> Envelope:
    return Envelope(code=code, data=data, message=message)


@router.get("/health")
def health() -> Envelope:
    return _env({"status": "up"})


@router.get("/stats", response_model=Envelope)
def stats() -> Envelope:
    return _env(StatsOut(**_pipeline.stats()).model_dump())


@router.post("/documents", status_code=201, response_model=Envelope)
def create_document(body: DocumentIn) -> Envelope:
    # Deterministic doc id -> check BEFORE ingesting to avoid duplicate chunks.
    doc = _pipeline.make_document(body.title, body.text)
    if _pipeline.has_document(doc.id):
        raise HTTPException(status_code=409, detail="duplicate document")
    doc_id, n_chunks = _pipeline.ingest_document(doc)
    if n_chunks == 0:
        raise HTTPException(status_code=400, detail="document produced zero chunks")
    return _env(
        DocumentOut(doc_id=doc_id, title=body.title, chunks=n_chunks).model_dump()
    )


@router.get("/documents", response_model=Envelope)
def list_documents() -> Envelope:
    return _env(_pipeline.list_documents())


@router.post("/query", response_model=None)
def query(body: QueryIn):  # returns Envelope (JSON) or StreamingResponse (SSE)
    if body.stream:
        return _sse_query(body)
    result = _pipeline.query(body.question, top_k=body.top_k, mode=body.mode)
    return _env(_query_out(result))


@router.post("/agent", response_model=Envelope)
def agent(body: AgentIn) -> Envelope:
    result = _agent.run(body.question)
    return _env(
        AgentOut(
            question=result.question,
            answer=result.answer,
            steps=[AgentStepOut(**vars(s)) for s in result.steps],
            tool_calls=result.tool_calls,
        ).model_dump()
    )


@router.post("/eval", response_model=Envelope)
def evaluate(body: EvalIn) -> Envelope:
    # Fresh pipeline inside run_eval -> deterministic, no runtime contamination.
    report = run_eval(default_golden_set(), top_k=body.top_k)
    return _env(report)


@router.get("/trace", response_model=Envelope)
def trace(question: str, top_k: int = 5) -> Envelope:
    return _env(_pipeline.retrieval_trace(question, top_k=top_k))


# -- helpers ------------------------------------------------------------------
def _query_out(result: object) -> dict[str, object]:
    from core.types import QueryAnswer

    r: QueryAnswer = result  # type: ignore[assignment]
    return QueryOut(
        question=r.question,
        answer=r.answer,
        provider=r.provider,
        retrieval_mode=r.retrieval_mode,
        citations=[CitationOut(**vars(c)) for c in r.citations],
    ).model_dump()


def _sse_query(body: QueryIn) -> StreamingResponse:
    def events() -> Iterator[str]:
        result = _pipeline.query(body.question, top_k=body.top_k, mode=body.mode)
        yield f"event: meta\ndata: {json.dumps({'provider': result.provider, 'citations': len(result.citations)}, ensure_ascii=False)}\n\n"
        for ch in result.answer:
            yield f"event: token\ndata: {json.dumps(ch, ensure_ascii=False)}\n\n"
        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")
