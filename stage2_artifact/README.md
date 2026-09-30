# Stage 2 — Public Artifact (gated)

**Do not start this stage until Stage 1 demonstrates zero-shot generalization**
(unseen tools/families/catalogs/models — see `stage1_core_paper/README.md`).

Release plan (design-doc sections 33 and 16):

- `dashboard/` — the Tool-Space Risk Predictor UI: candidate tool in, predicted
  interference level / expected degradation / risk interval / primary competing
  tools / recommendation out.
- `examples/` — worked examples reusing MCPEvol-Bench / MCP-Bench servers as the
  evaluation substrate (per the prior-art doc's Stage 2 recommendation), rather
  than a bespoke harness.
- A `ptim predict --model ... --catalog ... --candidate ... --workload ...` CLI.

Even a modest result here (method only slightly beats the Stage 0 cheap
baseline) is a legitimate release, provided the cheap baseline is reported
honestly alongside it.

Empty until the gate is met.
