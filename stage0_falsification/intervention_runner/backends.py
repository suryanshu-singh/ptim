"""Pluggable model backends for measuring tool-selection distributions.

A backend answers: given a query and a tool catalog, what empirical
distribution over tool names (plus "none") does the model produce when
sampled `n_samples` times at temperature > 0?

- MockBackend: TF-IDF cosine-similarity softmax simulator. Free, instant,
  deterministic given a seed. Exists ONLY to validate pipeline plumbing —
  see the warning in the top-level README. Because it is built from the
  same similarity signal the cheap baseline uses, it will make the cheap
  baseline look artificially strong; it cannot be used to falsify or
  confirm the PTIM hypothesis itself.
- AnthropicBackend: real tool-selection sampling via the Claude API.
  This is the backend Stage 0's actual falsification test requires.
"""
from __future__ import annotations

import abc
import os
from collections import Counter

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from stage0_falsification.common import Tool


class ModelBackend(abc.ABC):
    name: str

    @abc.abstractmethod
    def select_tool(self, query: str, tools: list[Tool], n_samples: int, seed: int) -> dict[str, float]:
        """Return an empirical distribution {tool_name_or_'none': probability} over n_samples draws."""
        raise NotImplementedError


class MockBackend(ModelBackend):
    name = "mock"

    def __init__(self, temperature: float = 0.6):
        self.temperature = temperature

    def _fit_vectorizer(self, query: str, tools: list[Tool]) -> TfidfVectorizer:
        corpus = [query] + [f"{t.name.replace('_', ' ')} {t.description}" for t in tools]
        vec = TfidfVectorizer(stop_words="english")
        vec.fit(corpus)
        return vec

    def select_tool(self, query: str, tools: list[Tool], n_samples: int, seed: int) -> dict[str, float]:
        vec = self._fit_vectorizer(query, tools)
        mat = vec.transform([query] + [f"{t.name.replace('_', ' ')} {t.description}" for t in tools]).toarray()
        q_vec, tool_vecs = mat[0], mat[1:]
        sims = np.array([
            float(np.dot(q_vec, tv) / (np.linalg.norm(q_vec) * np.linalg.norm(tv) + 1e-9))
            for tv in tool_vecs
        ])
        logits = sims / max(self.temperature, 1e-6)
        probs = np.exp(logits - logits.max())
        probs = probs / probs.sum()

        rng = np.random.default_rng(seed)
        draws = rng.choice(len(tools), size=n_samples, p=probs)
        counts = Counter(tools[i].name for i in draws)
        return {name: count / n_samples for name, count in counts.items()}


class AnthropicBackend(ModelBackend):
    """Synchronous, real-time backend. For a full Stage 0 run, prefer the
    batch-mode path in `batch_runner.py` instead -- it's 50% cheaper (Batch
    API pricing) and avoids re-sampling the baseline once per candidate.
    This class remains useful for quick interactive checks of a single
    (query, catalog) pair.
    """
    name = "anthropic"

    def __init__(
        self,
        model: str = "claude-haiku-4-5",
        temperature: float = 1.0,
        disable_thinking: bool = True,
        effort: str | None = None,
    ):
        try:
            import anthropic
        except ImportError as e:
            raise RuntimeError(
                "The 'anthropic' package is required for AnthropicBackend. "
                "Install it with `pip install anthropic`."
            ) from e
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set in the environment.")
        self._client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.temperature = temperature
        # Tool selection on these short synthetic queries doesn't benefit from
        # extended reasoning, and thinking tokens are billed as output even
        # when the summary display is omitted -- disabling it by default keeps
        # per-call cost small and predictable. `disable_thinking=True` requires
        # effort <= "high" (the default), which always holds here since effort
        # is left unset unless the caller opts into a specific level.
        self.disable_thinking = disable_thinking
        self.effort = effort

    def _create_kwargs(self, tool_schemas: list[dict], query: str) -> dict:
        kwargs: dict = dict(
            model=self.model,
            max_tokens=512,
            temperature=self.temperature,
            tools=tool_schemas,
            tool_choice={"type": "auto"},
            messages=[{"role": "user", "content": query}],
        )
        if self.disable_thinking:
            kwargs["thinking"] = {"type": "disabled"}
        if self.effort:
            kwargs["output_config"] = {"effort": self.effort}
        return kwargs

    def select_tool(self, query: str, tools: list[Tool], n_samples: int, seed: int) -> dict[str, float]:
        tool_schemas = [t.to_anthropic_schema() for t in tools]
        counts: Counter[str] = Counter()

        for _ in range(n_samples):
            response = self._client.messages.create(**self._create_kwargs(tool_schemas, query))
            tool_uses = [b for b in response.content if b.type == "tool_use"]
            if tool_uses:
                counts[tool_uses[0].name] += 1
            else:
                counts["none"] += 1

        return {name: count / n_samples for name, count in counts.items()}


def build_backend(name: str, **kwargs) -> ModelBackend:
    if name == "mock":
        return MockBackend(**kwargs)
    if name == "anthropic":
        return AnthropicBackend(**kwargs)
    raise ValueError(f"Unknown backend: {name}")
