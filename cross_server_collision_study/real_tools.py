"""Real tool definitions pulled from currently-deployed, independently-authored
MCP servers (fetched 2026-08-27 from their public source/README).

Sources:
  filesystem, git, memory, time -- official modelcontextprotocol/servers reference servers
  github                        -- github/github-mcp-server (real, ~79 tools; subset used here)
  brave                         -- modelcontextprotocol/servers-archived/src/brave-search
  tavily                        -- tavily-ai/tavily-mcp
  exa                           -- exa-labs/exa-mcp-server
  slack                         -- modelcontextprotocol/servers-archived/src/slack
  discord                       -- SaseQ/discord-mcp (subset)

`family` on each Tool is used here only as a namespace/server tag, not a
train/test split label like in stage0_falsification.
"""
from __future__ import annotations

from stage0_falsification.common import Tool


def _t(name, family, description, schema, required=None):
    return Tool(name=name, description=description, family=family,
                input_schema=schema, required_fields=required)


# ---------------------------------------------------------------- filesystem
FILESYSTEM = [
    _t("read_text_file", "filesystem",
       "Read the complete contents of a file from the file system as text. Handles various text "
       "encodings and provides detailed error messages if the file cannot be read.",
       {"path": "string", "tail": "number", "head": "number"}, ["path"]),
    _t("read_file", "filesystem",
       "Read the complete contents of a file as text. DEPRECATED: Use read_text_file instead.",
       {"path": "string", "tail": "number", "head": "number"}, ["path"]),
    _t("read_media_file", "filesystem",
       "Read a file and return it as a base64-encoded content block with its MIME type.",
       {"path": "string"}, ["path"]),
    _t("read_multiple_files", "filesystem",
       "Read the contents of multiple files simultaneously. More efficient than reading files one by one.",
       {"paths": "array"}, ["paths"]),
    _t("write_file", "filesystem",
       "Create a new file or completely overwrite an existing file with new content.",
       {"path": "string", "content": "string"}, ["path", "content"]),
    _t("edit_file", "filesystem",
       "Make line-based edits to a text file. Each edit replaces exact line sequences with new content.",
       {"path": "string", "edits": "array", "dryRun": "boolean"}, ["path", "edits"]),
    _t("create_directory", "filesystem",
       "Create a new directory or ensure a directory exists. Can create multiple nested directories.",
       {"path": "string"}, ["path"]),
    _t("list_directory", "filesystem",
       "Get a detailed listing of all files and directories in a specified path.",
       {"path": "string"}, ["path"]),
    _t("list_directory_with_sizes", "filesystem",
       "Get a detailed listing of all files and directories in a specified path, including sizes.",
       {"path": "string", "sortBy": "string"}, ["path"]),
    _t("directory_tree", "filesystem",
       "Get a recursive tree view of files and directories as a JSON structure.",
       {"path": "string", "excludePatterns": "array"}, ["path"]),
    _t("move_file", "filesystem",
       "Move or rename files and directories.",
       {"source": "string", "destination": "string"}, ["source", "destination"]),
    _t("search_files", "filesystem",
       "Recursively search for files and directories matching a glob-style pattern.",
       {"path": "string", "pattern": "string", "excludePatterns": "array"}, ["path", "pattern"]),
    _t("get_file_info", "filesystem",
       "Retrieve detailed metadata about a file or directory (size, times, permissions, type).",
       {"path": "string"}, ["path"]),
    _t("list_allowed_directories", "filesystem",
       "Returns the list of directories that this server is allowed to access.",
       {}, []),
]

# ----------------------------------------------------------------------- git
GIT = [
    _t("git_status", "git", "Shows the working tree status", {"repo_path": "string"}, ["repo_path"]),
    _t("git_diff_unstaged", "git", "Shows changes in the working directory that are not yet staged",
       {"repo_path": "string", "context_lines": "integer"}, ["repo_path"]),
    _t("git_diff_staged", "git", "Shows changes that are staged for commit",
       {"repo_path": "string", "context_lines": "integer"}, ["repo_path"]),
    _t("git_diff", "git", "Shows differences between branches or commits",
       {"repo_path": "string", "target": "string", "context_lines": "integer"}, ["repo_path", "target"]),
    _t("git_commit", "git", "Records changes to the repository",
       {"repo_path": "string", "message": "string"}, ["repo_path", "message"]),
    _t("git_add", "git", "Adds file contents to the staging area",
       {"repo_path": "string", "files": "array"}, ["repo_path", "files"]),
    _t("git_reset", "git", "Unstages all staged changes", {"repo_path": "string"}, ["repo_path"]),
    _t("git_log", "git", "Shows the commit logs",
       {"repo_path": "string", "max_count": "integer", "start_timestamp": "string", "end_timestamp": "string"},
       ["repo_path"]),
    _t("git_create_branch", "git", "Creates a new branch from an optional base branch",
       {"repo_path": "string", "branch_name": "string", "base_branch": "string"}, ["repo_path", "branch_name"]),
    _t("git_checkout", "git", "Switches branches",
       {"repo_path": "string", "branch_name": "string"}, ["repo_path", "branch_name"]),
    _t("git_show", "git", "Shows the contents of a commit",
       {"repo_path": "string", "revision": "string"}, ["repo_path", "revision"]),
    _t("git_branch", "git", "List Git branches",
       {"repo_path": "string", "branch_type": "string", "contains": "string", "not_contains": "string"},
       ["repo_path", "branch_type"]),
]

# -------------------------------------------------------------------- memory
MEMORY = [
    _t("create_entities", "memory", "Create multiple new entities in the knowledge graph",
       {"entities": "array"}, ["entities"]),
    _t("create_relations", "memory",
       "Create multiple new relations between entities in the knowledge graph. Relations should be active voice",
       {"relations": "array"}, ["relations"]),
    _t("add_observations", "memory", "Add new observations to existing entities in the knowledge graph",
       {"observations": "array"}, ["observations"]),
    _t("delete_entities", "memory", "Delete multiple entities and their associated relations",
       {"entityNames": "array"}, ["entityNames"]),
    _t("delete_observations", "memory", "Delete specific observations from entities in the knowledge graph",
       {"deletions": "array"}, ["deletions"]),
    _t("delete_relations", "memory", "Delete multiple relations from the knowledge graph",
       {"relations": "array"}, ["relations"]),
    _t("read_graph", "memory", "Read the entire knowledge graph", {}, []),
    _t("search_nodes", "memory", "Search for nodes in the knowledge graph based on a query",
       {"query": "string"}, ["query"]),
    _t("open_nodes", "memory", "Open specific nodes in the knowledge graph by their names",
       {"names": "array"}, ["names"]),
]

# ---------------------------------------------------------------------- time
TIME = [
    _t("get_current_time", "time", "Get current time in a specific timezone",
       {"timezone": "string"}, ["timezone"]),
    _t("convert_time", "time", "Convert time between timezones",
       {"source_timezone": "string", "time": "string", "target_timezone": "string"},
       ["source_timezone", "time", "target_timezone"]),
]

# -------------------------------------------------------------------- github
# Real tool set is ~79; using a representative, lower-parameter-count subset
# for cost control (large param-heavy tools like issue_write/projects_write excluded).
GITHUB = [
    _t("star_repository", "github", "Star repository", {"owner": "string", "repo": "string"},
       ["owner", "repo"]),
    _t("unstar_repository", "github", "Unstar repository", {"owner": "string", "repo": "string"},
       ["owner", "repo"]),
    _t("list_branches", "github", "List repository branches",
       {"owner": "string", "repo": "string", "page": "integer", "perPage": "integer"}, ["owner", "repo"]),
    _t("create_branch", "github", "Create repository branch",
       {"owner": "string", "repo": "string", "branch": "string", "from_branch": "string"},
       ["owner", "repo", "branch"]),
    _t("get_file_contents", "github", "Retrieve file or directory contents",
       {"owner": "string", "repo": "string", "path": "string", "ref": "string"}, ["owner", "repo"]),
    _t("list_commits", "github", "List repository commits",
       {"owner": "string", "repo": "string", "author": "string", "since": "string", "until": "string"},
       ["owner", "repo"]),
    _t("get_commit", "github", "Retrieve commit details",
       {"owner": "string", "repo": "string", "sha": "string"}, ["owner", "repo", "sha"]),
    _t("search_repositories", "github", "Search repositories", {"query": "string"}, ["query"]),
    _t("search_code", "github", "Search repository code", {"query": "string"}, ["query"]),
    _t("search_users", "github", "Search for users", {"query": "string"}, ["query"]),
    _t("search_orgs", "github", "Search for organizations", {"query": "string"}, ["query"]),
    _t("list_tags", "github", "List repository tags",
       {"owner": "string", "repo": "string"}, ["owner", "repo"]),
    _t("get_tag", "github", "Retrieve tag details",
       {"owner": "string", "repo": "string", "tag": "string"}, ["owner", "repo", "tag"]),
    _t("list_releases", "github", "List repository releases",
       {"owner": "string", "repo": "string"}, ["owner", "repo"]),
    _t("get_latest_release", "github", "Retrieve most recent release",
       {"owner": "string", "repo": "string"}, ["owner", "repo"]),
    _t("fork_repository", "github", "Fork existing repository",
       {"owner": "string", "repo": "string", "organization": "string"}, ["owner", "repo"]),
    _t("create_repository", "github", "Create new repository",
       {"name": "string", "description": "string", "private": "boolean"}, ["name"]),
    _t("list_starred_repositories", "github", "List starred repositories", {"username": "string"}, []),
    _t("list_gists", "github", "List Gists", {"username": "string"}, []),
    _t("get_gist", "github", "Retrieve Gist content", {"gist_id": "string"}, ["gist_id"]),
    _t("create_gist", "github", "Create new Gist",
       {"filename": "string", "content": "string", "description": "string"}, ["filename", "content"]),
    _t("list_notifications", "github", "List user notifications", {"owner": "string", "repo": "string"}, []),
    _t("mark_all_notifications_read", "github", "Mark all notifications as read", {}, []),
    _t("get_teams", "github", "Retrieve team data", {"user": "string"}, []),
    _t("get_team_members", "github", "Retrieve team member information",
       {"org": "string", "team_slug": "string"}, ["org", "team_slug"]),
    _t("list_label", "github", "List repository labels",
       {"owner": "string", "repo": "string"}, ["owner", "repo"]),
    _t("get_label", "github", "Retrieve specific label information",
       {"owner": "string", "repo": "string", "name": "string"}, ["owner", "repo", "name"]),
    _t("list_dependabot_alerts", "github", "List Dependabot alerts",
       {"owner": "string", "repo": "string"}, ["owner", "repo"]),
    _t("get_dependabot_alert", "github", "Retrieve Dependabot alert details",
       {"owner": "string", "repo": "string", "alertNumber": "integer"}, ["owner", "repo", "alertNumber"]),
    _t("list_repository_collaborators", "github", "List repository collaborators",
       {"owner": "string", "repo": "string"}, ["owner", "repo"]),
]

# ------------------------------------------------------------- brave search
BRAVE = [
    _t("brave_web_search", "brave",
       "Performs a web search using the Brave Search API, ideal for general queries, news, articles, "
       "and online content, with support for pagination and content filtering.",
       {"query": "string", "count": "number", "offset": "number"}, ["query"]),
    _t("brave_local_search", "brave",
       "Searches for local businesses and places using Brave's Local Search API, optimized for "
       "physical locations, businesses, and services -- names, addresses, ratings, phone numbers, hours.",
       {"query": "string", "count": "number"}, ["query"]),
]

# ------------------------------------------------------------------ tavily
TAVILY = [
    _t("tavily_search", "tavily",
       "Search the web for current information on any topic. Use for news, facts, or data beyond "
       "your knowledge cutoff. Returns snippets and source URLs.",
       {"query": "string", "search_depth": "string", "max_results": "number"}, ["query"]),
    _t("tavily_extract", "tavily",
       "Extract content from URLs. Returns raw page content in markdown or text format.",
       {"urls": "array", "format": "string"}, ["urls"]),
    _t("tavily_crawl", "tavily",
       "Crawl a website starting from a URL. Extracts content from pages with configurable depth and breadth.",
       {"url": "string", "max_depth": "integer", "max_breadth": "integer"}, ["url"]),
    _t("tavily_map", "tavily",
       "Map a website's structure. Returns a list of URLs found starting from the base URL.",
       {"url": "string", "max_depth": "integer"}, ["url"]),
    _t("tavily_research", "tavily",
       "Perform comprehensive research on a given topic or question, gathering information from "
       "multiple sources to answer a question or complete a task.",
       {"input": "string", "model": "string"}, ["input"]),
]

# --------------------------------------------------------------------- exa
EXA = [
    _t("web_search_exa", "exa",
       "Search the web for any topic and get clean, ready-to-use content. Best for: finding current "
       "information, news, facts, people, companies, or answering questions about any topic.",
       {"query": "string", "numResults": "number"}, ["query"]),
]

# ------------------------------------------------------------------- slack
SLACK = [
    _t("slack_list_channels", "slack", "List public or pre-defined channels in the workspace with pagination",
       {"limit": "number", "cursor": "string"}, []),
    _t("slack_post_message", "slack", "Post a new message to a Slack channel",
       {"channel_id": "string", "text": "string"}, ["channel_id", "text"]),
    _t("slack_reply_to_thread", "slack", "Reply to a specific message thread in Slack",
       {"channel_id": "string", "thread_ts": "string", "text": "string"},
       ["channel_id", "thread_ts", "text"]),
    _t("slack_add_reaction", "slack", "Add a reaction emoji to a message",
       {"channel_id": "string", "timestamp": "string", "reaction": "string"},
       ["channel_id", "timestamp", "reaction"]),
    _t("slack_get_channel_history", "slack", "Get recent messages from a channel",
       {"channel_id": "string", "limit": "number"}, ["channel_id"]),
    _t("slack_get_thread_replies", "slack", "Get all replies in a message thread",
       {"channel_id": "string", "thread_ts": "string"}, ["channel_id", "thread_ts"]),
    _t("slack_get_users", "slack", "Get a list of all users in the workspace with basic profile information",
       {"cursor": "string", "limit": "number"}, []),
    _t("slack_get_user_profile", "slack", "Get detailed profile information for a specific user",
       {"user_id": "string"}, ["user_id"]),
]

# ----------------------------------------------------------------- discord
# Real server exposes ~75 tools; representative subset used here for cost control.
DISCORD = [
    _t("send_message", "discord", "Send a message to a specific channel",
       {"channel_id": "string", "content": "string"}, ["channel_id", "content"]),
    _t("edit_message", "discord", "Edit a message from a specific channel",
       {"channel_id": "string", "message_id": "string", "content": "string"},
       ["channel_id", "message_id", "content"]),
    _t("delete_message", "discord", "Delete a message from a specific channel",
       {"channel_id": "string", "message_id": "string"}, ["channel_id", "message_id"]),
    _t("read_messages", "discord", "Read message history from a specific channel",
       {"channel_id": "string", "count": "integer"}, ["channel_id"]),
    _t("add_reaction", "discord", "Add a reaction emoji to a specific message",
       {"channel_id": "string", "message_id": "string", "emoji": "string"},
       ["channel_id", "message_id", "emoji"]),
    _t("remove_reaction", "discord", "Remove a specified reaction emoji from a message",
       {"channel_id": "string", "message_id": "string", "emoji": "string"},
       ["channel_id", "message_id", "emoji"]),
    _t("send_private_message", "discord", "Send a private message to a specific user",
       {"user_id": "string", "content": "string"}, ["user_id", "content"]),
    _t("read_private_messages", "discord", "Read private message history from a specific user",
       {"user_id": "string", "count": "integer"}, ["user_id"]),
    _t("list_channels", "discord", "List of all channels", {"guild_id": "string"}, ["guild_id"]),
    _t("get_channel_info", "discord", "Get detailed information about a channel",
       {"channel_id": "string"}, ["channel_id"]),
    _t("find_channel", "discord", "Find a channel type and ID using name and server ID",
       {"guild_id": "string", "channel_name": "string"}, ["guild_id", "channel_name"]),
    _t("create_text_channel", "discord", "Create a new text channel",
       {"guild_id": "string", "channel_name": "string"}, ["guild_id", "channel_name"]),
    _t("get_server_info", "discord", "Get detailed discord server information",
       {"guild_id": "string"}, ["guild_id"]),
    _t("get_user_id_by_name", "discord", "Get a Discord user's ID by username in a guild for ping usage",
       {"guild_id": "string", "username": "string"}, ["guild_id", "username"]),
    _t("list_roles", "discord", "Get a list of all roles on the server with their details",
       {"guild_id": "string"}, ["guild_id"]),
]
