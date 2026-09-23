# Author: 晨星
"""Zero-dependency tokenizer for BM25. CJK characters are emitted as
unigrams + bigrams; latin runs are emitted as lowercase words.
Avoids jieba (sdist-only on Windows, needs a compiler)."""
from __future__ import annotations

import re

_CJK_RE = re.compile(r"[一-鿿㐀-䶿]")
_LATIN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    """Split text into BM25 terms (CJK unigram+bigram, latin words)."""
    tokens: list[str] = []
    cjk_run: list[str] = []
    lower = text.lower()

    def flush_cjk() -> None:
        tokens.extend(cjk_run)
        tokens.extend(cjk_run[i] + cjk_run[i + 1] for i in range(len(cjk_run) - 1))
        cjk_run.clear()

    pos = 0
    for m in re.finditer(r"[一-鿿㐀-䶿]+|[a-z0-9]+|[^一-鿿㐀-䶿a-z0-9]+", lower):
        seg = m.group(0)
        if _CJK_RE.match(seg):
            cjk_run.extend(seg)
        else:
            flush_cjk()
            if _LATIN_RE.fullmatch(seg):
                tokens.append(seg)
        pos = m.end()
    flush_cjk()
    return tokens
