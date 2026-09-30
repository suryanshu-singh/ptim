"""Builds the 10 experimental catalog conditions: 2 backbone sizes (small=15,
large=45 real, non-overlapping tools) x 5 collision-degree conditions
(search 1/2/3-way, messaging 1/2-way).

Connecting a real MCP server means including ALL of that server's tools in
this experiment's real_tools.py (as it would be in practice) -- collision
"degree" is which independently-authored servers are connected, not a count
of individually cherry-picked tools.
"""
from __future__ import annotations

from stage0_falsification.common import Catalog
from cross_server_collision_study import real_tools as rt

_fs = {t.name: t for t in rt.FILESYSTEM}
_git = {t.name: t for t in rt.GIT}
_mem = {t.name: t for t in rt.MEMORY}
_gh = {t.name: t for t in rt.GITHUB}

SMALL_BACKBONE = [
    _fs["read_text_file"], _fs["write_file"], _fs["list_directory"], _fs["search_files"], _fs["get_file_info"],
    _git["git_status"], _git["git_commit"], _git["git_log"], _git["git_diff"], _git["git_branch"],
    _mem["search_nodes"], _mem["create_entities"], _mem["read_graph"],
    rt.TIME[0], rt.TIME[1],
]
assert len(SMALL_BACKBONE) == 15

LARGE_BACKBONE = SMALL_BACKBONE + [
    _fs["read_file"], _fs["read_media_file"], _fs["read_multiple_files"], _fs["edit_file"],
    _fs["create_directory"], _fs["list_directory_with_sizes"], _fs["directory_tree"],
    _fs["move_file"], _fs["list_allowed_directories"],
    _git["git_diff_unstaged"], _git["git_diff_staged"], _git["git_add"], _git["git_reset"],
    _git["git_create_branch"], _git["git_checkout"], _git["git_show"],
    _mem["create_relations"], _mem["add_observations"], _mem["delete_entities"],
    _mem["delete_observations"], _mem["delete_relations"], _mem["open_nodes"],
    _gh["star_repository"], _gh["list_branches"], _gh["create_branch"], _gh["get_file_contents"],
    _gh["list_commits"], _gh["search_repositories"], _gh["get_commit"], _gh["list_tags"],
]
assert len(LARGE_BACKBONE) == 45

SEARCH_DEGREE = {
    1: rt.BRAVE,
    2: rt.BRAVE + rt.TAVILY,
    3: rt.BRAVE + rt.TAVILY + rt.EXA,
}

MESSAGING_DEGREE = {
    1: rt.SLACK,
    2: rt.SLACK + rt.DISCORD,
}


def build_conditions() -> dict[str, Catalog]:
    """Returns condition_id -> Catalog for all 10 conditions."""
    conditions = {}
    for backbone_name, backbone in [("small", SMALL_BACKBONE), ("large", LARGE_BACKBONE)]:
        for degree, cluster_tools in SEARCH_DEGREE.items():
            cid = f"search_d{degree}_{backbone_name}"
            conditions[cid] = Catalog(catalog_id=cid, family="search",
                                       tools=list(backbone) + list(cluster_tools))
        for degree, cluster_tools in MESSAGING_DEGREE.items():
            cid = f"messaging_d{degree}_{backbone_name}"
            conditions[cid] = Catalog(catalog_id=cid, family="messaging",
                                       tools=list(backbone) + list(cluster_tools))
    return conditions
