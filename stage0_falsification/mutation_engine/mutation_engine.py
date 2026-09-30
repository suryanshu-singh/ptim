"""Generates candidate tool additions of the five kinds from design-doc section 17:

  A. random               - semantically unrelated tool (near-zero-interference control)
  B. near_duplicate        - same capability & schema, reworded name/description
  C. schema_confusable      - same parameter shape, different capability
  D. description_confusable - overlapping description vocabulary, different schema/capability
  E. mixed_realistic         - a plausible new, genuinely distinct capability for the family
"""
from __future__ import annotations

from stage0_falsification.common import Tool
from stage0_falsification.mutation_engine.foreign_pool import foreign_tool_for

MUTATION_TYPES = ["random", "near_duplicate", "schema_confusable", "description_confusable", "mixed_realistic"]

_SYNONYMS = {
    "create": "schedule", "new": "fresh", "event": "meeting", "list": "show",
    "delete": "remove", "update": "modify", "existing": "current", "find": "locate",
    "set": "configure", "get": "fetch", "retrieve": "fetch", "add": "register",
    "search": "look up", "log": "record", "generate": "produce", "check": "verify",
    "transfer": "move", "review": "inspect", "draft": "compose", "lookup": "look up",
    "run": "execute", "deploy": "release", "book": "reserve", "cancel": "revoke",
}

# One genuinely distinct, plausible additional capability per family, representative
# of realistic enterprise catalog growth (design-doc section 17E).
_MIXED_REALISTIC: dict[str, Tool] = {
    "calendar": Tool("sync_calendar_provider", "Sync events between this calendar and an external calendar provider account.",
                      "calendar", {"provider": "string", "account_id": "string"}, mutation_type="mixed_realistic"),
    "crm": Tool("merge_duplicate_contacts", "Merge two duplicate CRM contact records into one, combining their activity history.",
                "crm", {"primary_contact_id": "string", "duplicate_contact_id": "string"}, mutation_type="mixed_realistic"),
    "finance": Tool("reconcile_statement", "Reconcile a bank statement against recorded transactions and flag discrepancies.",
                    "finance", {"account_id": "string", "statement_id": "string"}, mutation_type="mixed_realistic"),
    "travel": Tool("request_visa_check", "Check visa requirements for a passenger's nationality traveling to a destination country.",
                   "travel", {"nationality": "string", "destination": "string"}, mutation_type="mixed_realistic"),
    "legal": Tool("calculate_statute_of_limitations", "Calculate the statute-of-limitations deadline for a given claim type and jurisdiction.",
                  "legal", {"claim_type": "string", "jurisdiction": "string", "incident_date": "string"}, mutation_type="mixed_realistic"),
    "developer_tools": Tool("provision_dev_environment", "Provision a new ephemeral development environment for a branch.",
                            "developer_tools", {"branch": "string", "template": "string"}, mutation_type="mixed_realistic"),
    "email": Tool("unsubscribe_from_sender", "Unsubscribe from future emails sent by a specific sender address.",
                  "email", {"sender_email": "string"}, mutation_type="mixed_realistic"),
    "project_management": Tool("generate_burndown_chart", "Generate a burndown chart for an active sprint.",
                                "project_management", {"sprint_id": "string"}, mutation_type="mixed_realistic"),
}


def _reword(text: str) -> str:
    words = text.split(" ")
    return " ".join(_SYNONYMS.get(w.strip(".,").lower(), w) for w in words)


def make_random(family: str, seed: int) -> Tool:
    base = foreign_tool_for(seed)
    return Tool(base.name, base.description, family, dict(base.input_schema),
                mutation_type="random", base_tool=None)


def make_near_duplicate(base: Tool) -> Tool:
    first_word = base.name.split('_')[0]
    # Tool names must be a single valid identifier -- some _SYNONYMS values are
    # multi-word phrases ("search" -> "look up"), which is fine inside a
    # reworded description sentence but produces an invalid, API-rejected tool
    # name (a literal space) if spliced in unsanitized here.
    replacement = _SYNONYMS.get(first_word, first_word).replace(" ", "")
    new_name = f"{replacement}_{'_'.join(base.name.split('_')[1:])}"
    return Tool(
        name=new_name,
        description=_reword(base.description),
        family=base.family,
        input_schema=dict(base.input_schema),  # identical schema: same underlying capability
        mutation_type="near_duplicate",
        base_tool=base.name,
    )


def make_schema_confusable(base: Tool, new_name: str, new_description: str) -> Tool:
    """Same parameter shape as `base`, but a different, unrelated capability."""
    return Tool(
        name=new_name,
        description=new_description,
        family=base.family,
        input_schema=dict(base.input_schema),  # identical schema on purpose
        mutation_type="schema_confusable",
        base_tool=base.name,
    )


def make_description_confusable(base: Tool, new_name: str, new_schema: dict[str, str]) -> Tool:
    """High lexical overlap with `base`'s description, but a different schema/capability."""
    borrowed = " ".join(base.description.split()[:6])
    return Tool(
        name=new_name,
        description=f"{borrowed} but instead handles a related, distinct operation with its own parameters.",
        family=base.family,
        input_schema=new_schema,
        mutation_type="description_confusable",
        base_tool=base.name,
    )


def make_mixed_realistic(family: str) -> Tool:
    return _MIXED_REALISTIC[family]
