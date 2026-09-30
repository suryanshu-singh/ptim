# PTIM: tool-selection interference in LLM agents

What happens to an agent's tool choices when you connect Claude to several
MCP servers at once, and their tools overlap?

This repo is a two-part experiment on `claude-haiku-4-5`, run against the real
Anthropic API (about 13,700 calls, roughly $13.50 in total). The first part tested
my original hypothesis and **the data disproved it**. The second part asked a
narrower question and got a clean answer.

## Result 1: my original hypothesis was wrong

**Hypothesis:** you can predict how much adding a new tool will hurt an agent's
tool selection from the *structure* of the catalog: schema overlap, lexical
overlap, and pairwise interference between tools.

**What the data said** (64 candidate tools added to 8 tool families, 9,000
calls):

- 53 of the 64 additions caused **exactly zero** change in selection accuracy.
- Of the 11 that had an effect, 8 were near-duplicates of an existing tool,
  and they account for almost all the damage: up to a 20 percentage-point
  accuracy drop. The other 3 moved accuracy by at most 3.2 points.
- A cheap 2-feature baseline (semantic similarity + catalog size) predicted the
  damage as well as the richer structural model. The structural features
  added nothing.

So the structural model wasn't worth building, and I stopped there instead of
scaling up. Along the way, the real runs also exposed two bugs in my own
harness (malformed tool names, and every schema field marked required). They
were fixed before the second run. Full write-up:
[docs/PTIM_Stage_0_5_Findings.md](docs/PTIM_Stage_0_5_Findings.md).

## Result 2: overlapping tools across real MCP servers make selection inconsistent

**Question:** real agents connect to MCP servers written by different
companies. Brave, Tavily and Exa each ship a "search the web" tool; Slack and
Discord each ship a "send a message" tool. Does that organic overlap confuse
the model, and does catalog size matter?

**Setup:** the real tool definitions from those servers, plus 15 or 45
unrelated real tools (filesystem, git, memory, time, GitHub) as filler. 10
conditions, 2,000 calls, 0 errors, $4.27.

**What the data said:**

| Overlapping servers | Search: selection entropy (15 → 45 filler tools) | Messaging: selection entropy |
|---|---|---|
| 1 (no real choice) | 0.000 → 0.000 | 0.000 → 0.000 |
| 2 | 0.141 → 0.242 | 0.242 → 0.242 |
| 3 | 0.586 → 0.692 | — |

Entropy is normalized: 0 means the same request always goes to the same tool;
1 means it's spread evenly across all the plausible tools.

- **More overlapping servers means less consistent choices,** and the pattern
  holds in both domains.
- **Adding unrelated tools makes an existing overlap worse.** In both search
  comparisons, 45 filler tools gave higher entropy than 15, even though none of
  the filler has anything to do with search.
- **The confusion stays local.** Unrelated tasks (time, git) were 100% accurate
  in every condition. Tasks that only one server can do (e.g. Brave's local
  search) were also 100% accurate: the model knows what each tool does. It just
  can't pick consistently between several equally valid options.
- **The preference is lopsided.** Tavily beat Brave 96–98% of the time, and
  Discord's tool beat Slack's 96%. *Caveat:* tool order wasn't
  counterbalanced, so this could be a real preference or a position bias in
  the tool list. I haven't separated the two yet.

**Why it matters in practice:** if a client connects several MCP servers with
overlapping tools, the same request can take different paths on different
runs. That hurts reproducibility, auditing and cost predictability, even
when every individual answer is "correct". Keeping each agent's tool set small
and free of overlap is the fix.

**Limitations:** one model, one run (not independently replicated), two domains
and two catalog sizes, and the ordering caveat above. Full write-up:
[docs/PTIM_Cross_Server_Collision_Findings.md](docs/PTIM_Cross_Server_Collision_Findings.md).

## Repo layout

```
docs/                          findings reports, experiment specs, prior-art review
stage0_falsification/          Result 1: catalog mutation, Claude sampling, baseline vs. structural model
cross_server_collision_study/  Result 2: real MCP server tool definitions, conditions, analysis
stage1_core_paper/             planned next stage; not started, because Result 1 said not to
stage2_artifact/               planned release stage; not started
```

The raw data behind every number above is in each study's `datasets/` folder
(`*_anthropic.json` are the real runs; `*_mock.json` are pipeline tests).

## Running it

Python 3.10+.

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Without an API key, the `mock` backend runs the whole pipeline end to end
against a simulator. That only checks the plumbing; it is not a result.

```bash
python stage0_falsification/run_stage0.py --backend mock
python cross_server_collision_study/run_study.py --backend mock
```

To reproduce the real runs, copy `.env.example` to `.env` and add an Anthropic
API key (pay-as-you-go; the key is loaded via `python-dotenv` and `.env` is
gitignored), then:

```bash
python stage0_falsification/run_stage0.py --backend anthropic
python cross_server_collision_study/run_study.py --backend anthropic --n-seeds 10
```

Both use the Batch API with thinking disabled to keep costs down. See
[stage0_falsification/README.md](stage0_falsification/README.md) for the cost
controls.
