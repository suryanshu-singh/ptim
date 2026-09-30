"""Shared data types for the Stage 0 falsification pipeline."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class Tool:
    name: str
    description: str
    family: str
    input_schema: dict[str, str]  # field_name -> type
    output_schema: dict[str, str] = field(default_factory=dict)
    mutation_type: str | None = None  # None for canonical tools
    base_tool: str | None = None  # name of the tool this one was mutated from, if any
    # Fields the model must supply to call this tool. None => every input_schema
    # field is required (safe default for mutated/candidate tools, which are
    # never a task's correct_tool so this never gets exercised). Canonical
    # tools that are task targets should set this explicitly: marking a truly
    # optional field (location, phone, notes, ...) required forces the model
    # to ask a clarifying question instead of calling the tool -- this was
    # confirmed empirically (real run, calendar family: model asked "what's
    # today's date" / "what location" instead of calling create_event, because
    # every field including optional ones was marked required).
    required_fields: list[str] | None = None

    def to_anthropic_schema(self) -> dict[str, Any]:
        """Render as an Anthropic API tool definition."""
        properties = {
            f: {"type": _json_type(t), "description": f.replace("_", " ")}
            for f, t in self.input_schema.items()
        }
        required = self.required_fields if self.required_fields is not None else list(self.input_schema.keys())
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        }

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _json_type(t: str) -> str:
    return {
        "string": "string",
        "integer": "integer",
        "number": "number",
        "array": "array",
        "object": "object",
        "boolean": "boolean",
    }.get(t, "string")


@dataclass
class Task:
    query: str
    family: str
    correct_tool: str


@dataclass
class Catalog:
    catalog_id: str
    family: str
    tools: list[Tool]

    def tool_names(self) -> list[str]:
        return [t.name for t in self.tools]

    def with_addition(self, candidate: Tool) -> "Catalog":
        return Catalog(
            catalog_id=f"{self.catalog_id}+{candidate.name}",
            family=self.family,
            tools=[*self.tools, candidate],
        )
