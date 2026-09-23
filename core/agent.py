# Author: 晨星
"""Minimal tool-calling agent (ReAct). With the mock LLM it runs a
heuristic plan (detect math -> calculator; else search -> summarize);
with a real LLM it parses 'Action: tool[input]' lines from generations.
Tools: search_knowledge, calculator, finish. Max 6 steps, loop-safe."""
from __future__ import annotations

import ast
import operator
import re

from .llm import LLMProvider
from .pipeline import RAGPipeline
from .types import AgentResult, AgentStep

MAX_STEPS = 6

_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY_OPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}


def safe_calc(expression: str) -> float:
    """Evaluate an arithmetic expression via AST whitelist (no eval)."""

    def _eval(node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
            return _BIN_OPS[type(node.op)](_eval(node.left), _eval(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
            return _UNARY_OPS[type(node.op)](_eval(node.operand))
        raise ValueError(f"unsupported expression: {ast.dump(node)}")

    tree = ast.parse(expression, mode="eval")
    return _eval(tree)


class Agent:
    """Tool-calling agent over a RAG pipeline."""

    def __init__(self, pipeline: RAGPipeline, llm: LLMProvider):
        self._pipeline = pipeline
        self._llm = llm

    def run(self, question: str) -> AgentResult:
        if self._looks_like_math(question):
            return self._run_math(question)
        return self._run_knowledge(question)

    # -- heuristic plans (deterministic, mock-friendly) ---------------------
    @staticmethod
    def _looks_like_math(question: str) -> bool:
        return bool(
            re.search(r"\d+\s*[-+*/×÷^]\s*\d+", question)
            or re.search(r"(计算|等于多少|多少是|算出)", question)
            and re.search(r"\d", question)
        )

    def _run_math(self, question: str) -> AgentResult:
        m = re.search(r"[\d.\s()+\-*/^]+", question.replace("×", "*").replace("÷", "/"))
        expr = m.group(0).strip() if m else ""
        expr = re.sub(r"\^", "**", expr)
        steps: list[AgentStep] = []
        try:
            value = safe_calc(expr)
            steps.append(
                AgentStep(
                    thought="问题包含算术表达式，调用计算器",
                    action="calculator",
                    action_input=expr,
                    observation=str(value),
                )
            )
            # Normalize: humans read 4 better than 4.0
            shown = int(value) if float(value).is_integer() else value
            answer = f"计算结果：{shown}"
        except (ValueError, SyntaxError, ZeroDivisionError) as exc:
            steps.append(
                AgentStep(
                    thought="表达式解析失败",
                    action="calculator",
                    action_input=expr,
                    observation=f"error: {exc}",
                )
            )
            answer = f"无法计算该表达式：{expr or question}"
        return AgentResult(question=question, answer=answer, steps=steps, tool_calls=1)

    def _run_knowledge(self, question: str) -> AgentResult:
        steps: list[AgentStep] = []
        result = self._pipeline.query(question)
        n_hits = len(result.citations)
        steps.append(
            AgentStep(
                thought="需要检索知识库后作答",
                action="search_knowledge",
                action_input=question,
                observation=f"retrieved {n_hits} chunks",
            )
        )
        if n_hits == 0:
            answer = "知识库为空或没有相关内容，请先摄入文档。"
        else:
            steps.append(
                AgentStep(
                    thought="基于检索结果生成摘要",
                    action="summarize",
                    action_input=f"{n_hits} chunks",
                    observation="answer generated",
                )
            )
            answer = result.answer
        return AgentResult(
            question=question, answer=answer, steps=steps, tool_calls=len(steps)
        )


# ReAct prompt kept for real LLM providers (documented protocol).
REACT_PROMPT = """你是一个工具调用 Agent。可用工具：
- search_knowledge[问题]：检索知识库
- calculator[算术表达式]：计算
- finish[最终答案]：结束
每轮输出两行：
Thought: 你的思考
Action: 工具名[输入]
已执行步骤：
{trajectory}
问题：{question}"""
