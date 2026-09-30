"""Task definitions for the cross-server collision study.

Two metric types:
  - "accuracy": a single designated correct_tool (standard P(correct) measurement,
    same as stage0_falsification) -- used for unrelated "collateral damage" checks
    and capability-specific checks (does the model wrongly reach for a look-alike
    that can't actually do the job).
  - "entropy": no single correct tool -- the task is genuinely ambiguous between
    the organically-overlapping real tools (e.g. "search the web" when 1-3 real
    search tools are present). Measured via the empirical distribution's entropy
    across seeds: does the model reliably pick the same one, or does it become
    less deterministic as more organically-similar options appear?
"""
from __future__ import annotations

from dataclasses import dataclass

from stage0_falsification.common import Catalog

SEARCH_AMBIGUOUS_VALID = {"brave_web_search", "tavily_search", "web_search_exa"}
MESSAGING_AMBIGUOUS_VALID = {"slack_post_message", "send_message"}


@dataclass
class CollisionTask:
    task_id: str
    query: str
    metric_type: str  # "accuracy" | "entropy"
    correct_tool: str | None = None
    valid_tools: list[str] | None = None


def tasks_for_condition(condition_id: str, catalog: Catalog) -> list[CollisionTask]:
    tool_names = set(catalog.tool_names())
    tasks: list[CollisionTask] = []

    if condition_id.startswith("search_"):
        present_search = sorted(SEARCH_AMBIGUOUS_VALID & tool_names)
        tasks.append(CollisionTask(
            "search_ambiguous", "Search the web for the current population of Japan.",
            "entropy", valid_tools=present_search,
        ))
        tasks.append(CollisionTask(
            "time_task", "What time is it in the timezone Asia/Tokyo?",
            "accuracy", correct_tool="get_current_time",
        ))
        tasks.append(CollisionTask(
            "git_task", "Show the working tree status of the repository at /home/user/project.",
            "accuracy", correct_tool="git_status",
        ))
        if "brave_local_search" in tool_names:
            tasks.append(CollisionTask(
                "brave_local_task", "Find pizza restaurants near Central Park.",
                "accuracy", correct_tool="brave_local_search",
            ))
        if "tavily_map" in tool_names:
            tasks.append(CollisionTask(
                "tavily_map_task",
                "Map the structure of the website https://example.com and return the list of URLs found.",
                "accuracy", correct_tool="tavily_map",
            ))

    elif condition_id.startswith("messaging_"):
        present_msg = sorted(MESSAGING_AMBIGUOUS_VALID & tool_names)
        tasks.append(CollisionTask(
            "messaging_ambiguous",
            "Send the message 'Deployment complete' to the channel with ID 1234567890123.",
            "entropy", valid_tools=present_msg,
        ))
        tasks.append(CollisionTask(
            "time_task", "What time is it in the timezone Asia/Tokyo?",
            "accuracy", correct_tool="get_current_time",
        ))
        tasks.append(CollisionTask(
            "git_task", "Show the working tree status of the repository at /home/user/project.",
            "accuracy", correct_tool="git_status",
        ))

    return tasks
