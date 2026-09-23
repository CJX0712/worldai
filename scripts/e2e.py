# Author: 晨星
"""Self-contained E2E: boot the real server process, wait for health,
then assert core success flows AND error flows over HTTP. Replaces the
docker-compose + curl pattern (unreliable in sandboxed environments).
Usage: python scripts/e2e.py   (exit 0 = all green)"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
PORT = int(os.environ.get("WORLDAI_E2E_PORT", "8791"))
BASE = f"http://127.0.0.1:{PORT}/api/v1"
STARTUP_TIMEOUT = 30

DOC = (
    "FAISS 是 Meta 开源的向量相似度搜索库，IndexFlatIP 提供精确内积搜索，"
    "对归一化向量等价于余弦相似度，广泛用于语义检索与 RAG 场景。" * 8
)

passed: list[str] = []
failed: list[tuple[str, str]] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if cond:
        passed.append(name)
    else:
        failed.append((name, detail))


def wait_for_health(client: httpx.Client, proc: subprocess.Popen[bytes]) -> bool:
    deadline = time.time() + STARTUP_TIMEOUT
    while time.time() < deadline:
        if proc.poll() is not None:
            return False
        try:
            r = client.get(f"{BASE}/health")
            if r.status_code == 200 and r.json()["data"]["status"] == "up":
                return True
        except httpx.TransportError:
            time.sleep(0.5)
    return False


def main() -> int:
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")
    proc = subprocess.Popen(
        [
            sys.executable,
            "-B",
            "-m",
            "uvicorn",
            "server.app:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(PORT),
        ],
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    try:
        with httpx.Client(timeout=30) as client:
            booted = wait_for_health(client, proc)
            check("server boots and /health returns up", booted)
            if not booted:
                out = proc.stdout.read().decode("utf-8", "replace") if proc.stdout else ""
                print(out[-3000:])
                return report()

            # -- success flows ------------------------------------------------
            r = client.post(f"{BASE}/documents", json={"title": "faiss.md", "text": DOC})
            check("POST /documents -> 201", r.status_code == 201, f"got {r.status_code}")
            doc_id = r.json()["data"]["doc_id"] if r.status_code == 201 else ""
            check(
                "document split into >=2 chunks",
                r.status_code == 201 and r.json()["data"]["chunks"] >= 2,
            )

            r = client.post(f"{BASE}/query", json={"question": "IndexFlatIP 是什么？"})
            qd = r.json().get("data", {})
            check("POST /query -> 200 + answer", r.status_code == 200 and bool(qd.get("answer")))
            check(
                "query returns citations from ingested doc",
                any(c.get("doc_id") == doc_id for c in qd.get("citations", [])),
            )

            r = client.post(
                f"{BASE}/query", json={"question": "FAISS 索引", "stream": True}
            )
            check(
                "SSE stream emits token + done events",
                r.status_code == 200 and "event: token" in r.text and "event: done" in r.text,
            )

            r = client.post(f"{BASE}/agent", json={"question": "计算 128 * 46"})
            check(
                "agent computes 128*46 = 5888",
                r.status_code == 200 and "5888" in r.json()["data"]["answer"],
            )

            r = client.post(f"{BASE}/agent", json={"question": "FAISS 支持哪些索引？"})
            steps = r.json()["data"]["steps"] if r.status_code == 200 else []
            check(
                "agent knowledge flow calls search_knowledge",
                any(s["action"] == "search_knowledge" for s in steps),
            )

            r = client.post(f"{BASE}/eval", json={"top_k": 3})
            agg = r.json()["data"]["aggregate"] if r.status_code == 200 else {}
            check("eval recall@1 == 1.0 on golden set", agg.get("recall@1") == 1.0, json.dumps(agg))

            r = client.get(f"{BASE}/stats")
            check(
                "stats reflects ingestion",
                r.status_code == 200 and r.json()["data"]["documents"] >= 1,
            )

            r = client.get(f"{BASE}/trace", params={"question": "FAISS 索引"})
            td = r.json().get("data", {})
            check(
                "trace exposes dense/bm25/fused orders",
                all(k in td for k in ("dense_order", "bm25_order", "fused_order")),
            )

            # -- error flows --------------------------------------------------
            r = client.post(f"{BASE}/documents", json={"title": "faiss.md", "text": DOC})
            check("duplicate document -> 409", r.status_code == 409, f"got {r.status_code}")

            r = client.post(f"{BASE}/documents", json={"title": "", "text": DOC})
            check("empty title -> 422", r.status_code == 422, f"got {r.status_code}")

            r = client.post(f"{BASE}/query", json={"question": ""})
            check("empty question -> 422", r.status_code == 422, f"got {r.status_code}")

            r = client.post(f"{BASE}/query", json={"question": "x", "top_k": 999})
            check("top_k out of range -> 422", r.status_code == 422, f"got {r.status_code}")
    finally:
        # Windows: kill the whole process tree, else the port leaks.
        subprocess.run(
            ["taskkill", "/pid", str(proc.pid), "/t", "/f"],
            capture_output=True,
        )
    return report()


def report() -> int:
    print(f"\nE2E result: {len(passed)} passed, {len(failed)} failed")
    for name in passed:
        print(f"  PASS  {name}")
    for name, detail in failed:
        print(f"  FAIL  {name}  {detail}")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
