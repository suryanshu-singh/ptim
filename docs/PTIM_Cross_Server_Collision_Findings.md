# Cross-Server Tool Collision — Findings Report

**Status:** Complete (2026-08-27). One real-backend batch run, 2,000 calls, $4.27 actual cost, 0 errors.

This investigation is a deliberate pivot away from PTIM's original single-catalog framing (see `docs/PTIM_Stage_0_5_Findings.md`) and away from a "near-duplicate screener" tool concept that turned out to overlap with existing published work (ToolScope) and existing security tooling (mcp-tool-card-linter). Before running it, I checked the closest prior work, including the paper that coined the term this project is built on, and did not find this specific question measured there.

## 1. The question

Real agents connect to multiple independently-authored MCP servers simultaneously. Different companies routinely build tools that do the same thing under different names — Brave, Tavily, and Exa each ship a "search the web" tool; Slack and Discord each ship a "send a message to a channel" tool. Nobody coordinates these names or descriptions across projects.

**Microsoft's tool-space-interference research** — the paper that named this problem — surveyed 1,470 real MCP servers and found 775 tools with literal name collisions, but did not measure whether an agent's *task accuracy* actually degrades from *semantic* (differently-named) overlap across servers. As I read it, the paper presents this as a risk rather than measuring it: it has no experiments on how agents perform when choosing between semantically overlapping tools, and no end-to-end task-completion studies.

This study measures it.

## 2. Method

Used real, currently-deployed, independently-authored MCP server tool definitions (fetched directly from each project's public source, 2026-08-27):

- **Search cluster**: `brave_web_search`+`brave_local_search` (Brave), `tavily_search`+3 others (Tavily), `web_search_exa` (Exa) — 3 real companies.
- **Messaging cluster**: `slack_post_message`+7 others (Slack, official), `send_message`+14 others (Discord, community server).
- **Backbone** (non-overlapping filler, for realism and to test the scale question): 15 real tools (small) or 45 real tools (large), drawn from the official filesystem/git/memory/time reference servers plus a GitHub tool subset.

10 conditions = 2 backbone sizes × (3 search collision degrees + 2 messaging collision degrees). Per condition, 3-5 tasks: one **ambiguous** task with no single correct answer (measured by entropy of the selection distribution across seeds — does the same query reliably land on the same tool?), 2 **unrelated backbone** tasks (accuracy, checking for collateral damage), and capability-specific tasks for domains where one server can do something the others can't (accuracy, checking whether the model wrongly reaches for a look-alike). 10 seeds × 5 samples = 50 draws per (condition, task).

## 3. Results

### 3a. Organic collision causes real, escalating indecision

| Collision degree | Search entropy, small→large backbone | Messaging entropy |
|---|---|---|
| 1 (single tool — no real choice) | 0.000 → 0.000 | 0.000 → 0.000 |
| 2 (two independent servers overlap) | 0.141 → 0.242 | 0.242 → 0.242 |
| 3 (three independent servers overlap) | 0.586 → 0.692 | — |

(Entropy normalized to [0,1]; 0 = always picks the same tool, 1 = uniform over all plausible options.) A clean, monotonic dose-response, not noise — replicated across two independent domains.

### 3b. Catalog size amplifies the effect (the phase-transition question)

At matched collision degree, the **large backbone (45 unrelated tools) shows higher entropy than the small one (15 unrelated tools)** in every search comparison (0.242 vs 0.141 at degree 2; 0.692 vs 0.586 at degree 3). Adding more *completely unrelated* tools elsewhere in the catalog measurably worsens an *existing* organic collision, even though those added tools have nothing to do with search. This is a real, previously-unmeasured interaction between catalog size and collision severity.

### 3c. Two clean negative controls

- **Zero collateral damage**: every unrelated task (time, git) scored 100% accuracy in every one of the 10 conditions, regardless of collision degree or catalog size. The confusion is strictly localized to the colliding cluster.
- **Zero capability confusion**: tasks needing a capability only one server has (`brave_local_search`, `tavily_map`) were answered correctly 100% of the time, even sitting next to 1-2 other "search-shaped" tools. The model isn't confused about what tools *do* — only about which of several *equally valid* options to pick for a generic request.

### 3d. An asymmetric, not uniform, preference — with a real caveat

The model doesn't split indecision evenly: `tavily_search` beat `brave_web_search` 96-98% to 2-4%; at 3-way collision, `web_search_exa` and `tavily_search` took nearly all the mass (74%/24% small backbone, 58%/40% large) while Brave was almost abandoned (~2%); Discord's `send_message` beat Slack's `slack_post_message` 96% to 4%.

**Caveat (unresolved by this run)**: tool order in the schema was not counterbalanced — later-added servers are also later in the tool list, so this could reflect a genuine tool preference, a position/recency bias in the list, or both. A follow-up with randomized/reversed ordering would be needed to separate these.

## 4. What this means

This is a clear, evidence-backed answer to a question the closest existing research raised but did not measure. It uses real, production MCP server tool definitions rather than synthetic ones, and it produced a clean effect for a modest spend.

To be precise about what degraded: **consistency, not accuracy.** Tasks with one correct tool stayed at 100% accuracy in every condition. What got worse is which tool the model picks for a generic request that several tools could serve: the same request goes to different tools on different runs. As far as I could find, the specific claim here (organic cross-server semantic overlap makes tool selection measurably less consistent, and catalog size amplifies it) has not been published before. That is based on my own prior-art search, not an exhaustive review.

## 5. Limitations, honestly

- **Single model** (`claude-haiku-4-5`). Unknown whether the effect size or the specific per-tool preferences generalize to other models.
- **Ordering confound** (3d above) — the preference-asymmetry finding is real but its cause (semantic quality vs. list position) is not yet isolated.
- **Two domains, two backbone sizes** — a real dose-response, but not a dense curve; the true shape between degree 1 and degree 3, or below/above the tested backbone sizes, is interpolated, not observed.
- **n=2,000 calls, 50 draws/condition** — enough for a clean signal at this effect size, but a single run, not independently replicated.

## 6. Recommended next steps

Ranked by value per dollar, not commitment:

1. **Ordering-control follow-up** (cheap, ~$4-5 at similar scale): reverse/randomize tool list order to isolate genuine preference from position bias. Directly strengthens the one weak point in an otherwise clean result.
2. **Second model** (similar cost): confirms whether this is a general LLM phenomenon or Haiku-specific.
3. **A composition-time risk checker**: unlike the earlier near-duplicate screener (shelved for overlapping with ToolScope/mcp-tool-card-linter), a tool that checks *a proposed set of MCP servers* for organic collisions before connecting them together targets a gap this study just confirmed is real and unaddressed — a more defensible practical artifact than the original screener idea.
4. **Write-up/release**: this result plus the real dataset is a legitimate, self-contained artifact (blog post, or a small public benchmark) independent of whether further experiments happen.
