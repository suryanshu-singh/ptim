"""Lightweight, dependency-light embedding proxy for the cheap baseline.

Uses TF-IDF over tool name+description text rather than a real embedding
model (sentence-transformers, an API embedding call, ...) so the cheap
baseline stays reproducible, free, and doesn't require network access or
an API key. Swapping in a real embedding model later is a drop-in change
behind this same `embed_tools` interface.
"""
from __future__ import annotations

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from stage0_falsification.common import Tool


def _text(t: Tool) -> str:
    return f"{t.name.replace('_', ' ')} {t.description}"


def fit_vectorizer(all_tools: list[Tool]) -> TfidfVectorizer:
    vec = TfidfVectorizer(stop_words="english")
    vec.fit([_text(t) for t in all_tools])
    return vec


def embed_tools(vec: TfidfVectorizer, tools: list[Tool]) -> np.ndarray:
    return vec.transform([_text(t) for t in tools]).toarray()


def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    denom = np.linalg.norm(a) * np.linalg.norm(b) + 1e-9
    return float(np.dot(a, b) / denom)


def max_mean_similarity(vec: TfidfVectorizer, candidate: Tool, catalog_tools: list[Tool]) -> tuple[float, float]:
    c_emb = embed_tools(vec, [candidate])[0]
    catalog_embs = embed_tools(vec, catalog_tools)
    sims = [cosine_sim(c_emb, e) for e in catalog_embs]
    return max(sims), sum(sims) / len(sims)
