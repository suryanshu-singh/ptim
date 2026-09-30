"""Builds baseline Catalog objects from the canonical tool families."""
from __future__ import annotations

from stage0_falsification.common import Catalog
from stage0_falsification.catalog_generator.tool_families import ALL_FAMILIES, FAMILY_TOOLS, FAMILY_TASKS


def build_baseline_catalogs() -> dict[str, Catalog]:
    """One baseline catalog per family, containing that family's canonical tools."""
    return {
        family: Catalog(catalog_id=f"{family}_baseline", family=family, tools=list(FAMILY_TOOLS[family]))
        for family in ALL_FAMILIES
    }


def tasks_for(family: str):
    return FAMILY_TASKS[family]
