# Predictive Tool Interference Modeling

## Predicting Agent Performance Damage Before a New Tool Is Exposed

**Working title:** Predictive Tool Interference Modeling (PTIM)  
**Potential system:** Tool-Space Risk Predictor (TSRP)  
**Domain:** LLM agents, MCP, tool use, AI engineering  
**Status:** Research hypothesis that survived a preliminary adversarial novelty review

---

# 1. Executive Summary

LLM agents increasingly operate over large and dynamically changing tool catalogs.

Recent research has established that:

- exposing more tools can degrade tool-selection performance;
- semantically overlapping tools can interfere with one another;
- tool descriptions and schemas affect selection;
- tool-set structure matters;
- higher-order interactions can occur;
- tool filtering and dynamic tool discovery can mitigate these effects.

Those findings are **not novel**.

The research opportunity explored here is narrower:

> **Can we predict the marginal behavioral damage that a new tool will cause to an agent before that tool is actually exposed to the agent?**

Formally, given:

- model \(M\);
- existing catalog \(C\);
- candidate tool \(t\);
- task/query distribution \(Q\);

predict:

\[
\hat{\Delta}(C,t,M,Q)
\]

where:

\[
\Delta(C,t,M,Q)
=
L(M,C\cup\{t\},Q)
-
L(M,C,Q)
\]

and \(L\) is a measurable loss such as:

- wrong-tool rate;
- task failure rate;
- extra tool-call count;
- latency;
- token cost.

The strongest version of the hypothesis goes further:

> **Learn a structural tool-interference model that predicts the full tool-selection distribution shift induced by an unseen tool, using pairwise and higher-order tool interactions.**

This proposal should **not** claim that tool interference itself is new.

The novelty hypothesis is specifically the **pre-deployment predictive layer**.

---

# 2. Novelty Verdict

## Current assessment

### Established and therefore not claimed as novel

- Tool-count degradation.
- Tool-space interference.
- Semantic tool overlap.
- Tool-set compatibility.
- Causal tool filtering.
- Tool pruning.
- Dynamic tool discovery.
- Schema and description effects.
- Tool-set interactions.
- Higher-order tool interactions.

### Potentially novel

> **Predicting the marginal performance effect of an unseen candidate tool before deploying it to the target agent/catalog.**

### More ambitious and potentially stronger

> **Predicting the entire tool-selection distribution shift caused by an unseen tool, and explaining the predicted shift through a learned structural interference model.**

### Strict caveat

This proposal has **not** established absolute academic or patent novelty. The current literature search did not surface an obvious direct predecessor for this exact predictive formulation, but a formal prior-art search is still required before publication or patent claims.

---

# 3. Problem Statement

Suppose an agent currently has:

\[
C = \{t_1,t_2,\ldots,t_n\}
\]

A platform is considering adding:

\[
t_{new}
\]

The conventional process is:

```text
Add tool
   ↓
Deploy
   ↓
Observe failures
   ↓
Diagnose
   ↓
Rollback or redesign
```

The proposed process is:

```text
Candidate tool
       ↓
Predict interference
       ↓
Estimate performance impact
       ↓
Decide whether to expose tool
       ↓
Deploy only if risk is acceptable
```

The key objective is **pre-deployment risk estimation**.

---

# 4. Formal Model

Let:

\[
P_C(T\mid q,M)
\]

be the probability distribution over tool selections for query \(q\), given catalog \(C\) and model \(M\).

After adding candidate tool \(x\):

\[
P_{C+x}(T\mid q,M)
\]

The policy shift is:

\[
D(q,x)
=
D\left(
P_C(T\mid q,M),
P_{C+x}(T\mid q,M)
\right)
\]

where \(D\) may be:

- KL divergence;
- Jensen-Shannon divergence;
- total variation distance;
- Wasserstein distance;
- task-specific probability movement.

The downstream performance effect is:

\[
\Delta L(q,x)
=
L(C+x,q)-L(C,q)
\]

The predictor estimates:

\[
\hat{\Delta L}(q,x)
\]

without observing the post-deployment outcome.

---

# 5. Why Predicting Distribution Shift Is Better Than Predicting Accuracy

A single accuracy change hides the mechanism.

For example:

### Before

```text
correct_tool      0.82
tool_B            0.06
tool_C            0.04
tool_D            0.02
```

### After adding tool X

```text
correct_tool      0.71
tool_B            0.14
tool_C            0.09
tool_D            0.02
tool_X            0.04
```

Task accuracy tells us:

\[
82\% \rightarrow 71\%
\]

But distributional analysis tells us:

> The probability mass moved primarily from the correct tool into tools B and C.

This can reveal the **mechanism of interference**.

---

# 6. Central Research Hypothesis

The central hypothesis is:

\[
\boxed{
\Delta L(C,x,M,Q)
\text{ is partially predictable from the structure of }
(C,x,M,Q)
}
\]

without executing the full post-addition workload.

More specifically:

\[
\hat{\Delta L}
=
f(
ToolFeatures,
CatalogStructure,
ModelFeatures,
TaskDistribution,
InteractionStructure
)
\]

The strongest version aims to explain the prediction structurally rather than using a black-box regression model.

---

# 7. Why Existing Tool-Interference Research Is Not Enough

Existing work establishes that interference occurs.

For example:

- Microsoft Research has documented **tool-space interference** at large MCP scale.
- HYSET studies tool-set compatibility and cardinality-specific interactions.
- CMTF-style work uses causal filtering to reduce unnecessary tool exposure.
- ToolScope and related systems prune or merge tools.
- Robust tool benchmarks study distractors, schema mutations, and interface perturbations.

But these approaches generally answer:

> "What happens when the tool set is already exposed?"

The proposed system asks:

> **"What will happen before we expose the candidate tool?"**

This creates a deployment-time decision problem.

---

# 8. Tool Interference as a Treatment Effect

Treat adding tool \(x\) as a treatment.

Baseline:

\[
Y_0 = L(M,C,Q)
\]

Treatment:

\[
Y_1 = L(M,C\cup\{x\},Q)
\]

The individual treatment effect is:

\[
ITE_x = Y_1-Y_0
\]

The average treatment effect over the task distribution is:

\[
ATE_x =
E_{q\sim Q}
[
L(C\cup\{x\},q)-L(C,q)
]
\]

The predictor attempts to estimate:

\[
\hat{ATE}_x
\]

before deployment.

This makes the problem naturally compatible with causal evaluation.

---

# 9. Counterfactual Training Data

Each training example contains:

```text
model
catalog
candidate_tool
task_distribution
baseline_behavior
post_addition_behavior
observed_delta
```

Example:

```json
{
  "model": "model_A",
  "catalog_id": "catalog_17",
  "candidate_tool": "search_transactions_v3",
  "baseline_accuracy": 0.918,
  "post_addition_accuracy": 0.887,
  "delta_accuracy": -0.031
}
```

The predictor receives only the information available **before deployment** when making its prediction.

The observed post-addition performance is held out as ground truth.

---

# 10. Tool Features

Candidate-tool features can include:

## Name

- token count;
- lexical overlap;
- verb similarity;
- noun similarity;
- naming patterns.

## Description

- embedding;
- length;
- semantic overlap;
- imperative language;
- examples;
- negative constraints;
- domain terminology.

## Input schema

- number of fields;
- field names;
- required/optional structure;
- types;
- enums;
- nesting depth.

## Output schema

- output fields;
- semantic overlap with other tools.

## Capability representation

An abstract capability vector:

\[
z_t
\]

should be learned from names, descriptions, and schemas.

---

# 11. Catalog Features

The predictor should model:

### Size

\[
N=|C|
\]

### Effective difficulty

For a task distribution \(Q\):

\[
N_{eff}
\]

or another effective-cardinality measure.

### Semantic density

How tightly tools cluster in capability space.

### Schema density

How many tools share similar parameter structures.

### Interference graph

\[
G_C
\]

### Tool centrality

How many other tools a candidate potentially competes with.

### Historical instability

How strongly similar tools have affected selection in the past.

---

# 12. Pairwise Interference

For tools \(i\) and \(j\):

\[
I_{ij}
=
E_q
[
P(i\mid q,C)
-
P(i\mid q,C\cup\{j\})
]
\]

This can produce:

```text
            Added Tool
             A      B      C
Existing A   --    .12    .01
Tool     B   .03    --    .21
         C   .01    .04     --
```

A high value indicates that adding \(j\) tends to move probability away from \(i\).

This is **not** claimed as novel by itself.

Its role is to provide structure for the predictive model.

---

# 13. Higher-Order Interactions

Pairwise effects may be insufficient.

For tools \(A,B,C\), it is possible that:

\[
I(A,B)\approx 0
\]

\[
I(A,C)\approx 0
\]

\[
I(B,C)\approx 0
\]

but:

\[
I(A,B,C)\gg 0
\]

This means a three-tool combination can create interference even when all pairwise interactions are weak.

The research question becomes:

> **How much predictive accuracy is lost by assuming pairwise additivity?**

---

# 14. Structural Prediction Model

Rather than simply using:

\[
\hat{\Delta}=MLP(features)
\]

the preferred formulation is:

\[
\hat{\Delta L}
=
\sum_i g(t,x_i)
+
\sum_{i<j} h(t,x_i,x_j)
+
r(C,x)
\]

where:

- \(g\) models pairwise contribution;
- \(h\) models higher-order interactions;
- \(r\) captures catalog-level effects.

Possible implementations:

- graph neural networks;
- hypergraph neural networks;
- factorization machines;
- neural relational models;
- sparse interaction models;
- structured generalized additive models.

---

# 15. Predictive Outputs

The system should predict:

### 1. Accuracy delta

\[
\hat{\Delta Accuracy}
\]

### 2. Wrong-tool probability shift

\[
\hat{\Delta P(T_i)}
\]

### 3. Expected additional calls

\[
\hat{\Delta Calls}
\]

### 4. Latency impact

\[
\hat{\Delta Latency}
\]

### 5. Token cost impact

\[
\hat{\Delta Tokens}
\]

### 6. Risk interval

\[
[\hat{\Delta}-\epsilon_1,
 \hat{\Delta}+\epsilon_2]
\]

A calibrated interval is preferable to a point prediction.

---

# 16. Tool-Space Risk Predictor

A production-oriented system could expose:

```text
Candidate Tool:
search_transactions_v3

Predicted selection interference:
HIGH

Expected task degradation:
-2.7 pp

90% interval:
[-3.8 pp, -1.6 pp]

Primary competing tools:
search_orders
lookup_payments

Likely mechanism:
semantic + schema overlap

Recommendation:
Do not expose globally.
Prefer scoped exposure.
```

This is the end-user value of the research.

---

# 17. Candidate Experiment: 30 → 300 Tools

Start with:

```text
30 tools
100 tools
300 tools
```

Generate controlled catalogs with:

### A. Random additions

Semantically unrelated tools.

### B. Near-duplicates

Highly similar capabilities.

### C. Schema-confusable

Similar parameters but different behavior.

### D. Description-confusable

Similar natural-language descriptions.

### E. Mixed realistic catalog

A realistic enterprise/MCP catalog.

---

# 18. Training / Test Split

The key methodological requirement is:

> **The predictor must generalize to unseen tools.**

Do not randomly split tool instances if nearly identical tools occur in both train and test.

Use:

### Tool-family split

Train:

```text
calendar
CRM
finance
```

Test:

```text
travel
legal
developer tools
```

### Provider split

Train on providers A/B/C.

Test on unseen provider D.

### Capability split

Train on some capability families.

Test on unseen capability combinations.

### Catalog split

Train on catalogs 1–20.

Test on completely held-out catalogs.

This prevents leakage.

---

# 19. Killer Experiment

For every held-out candidate tool \(x\):

### Before deployment

Compute:

\[
\hat{\Delta L}
\]

### Then actually deploy

Measure:

\[
\Delta L
\]

The primary metric is:

\[
MAE=
\frac{1}{N}
\sum_i
|\hat{\Delta L_i}-\Delta L_i|
\]

Also report:

\[
RMSE
\]

\[
R^2
\]

\[
Spearman(\hat{\Delta},\Delta)
\]

and calibration error.

---

# 20. The Strongest Test

## Zero-Shot Tool Addition

The candidate tool should be completely unseen during predictor training.

For example:

```text
Training:
finance + calendar + CRM tools

Test:
new logistics tool
```

The predictor sees:

```text
name
description
schema
catalog
model
```

but never saw the actual tool or its measured effect.

Then:

\[
\hat{\Delta}
\]

is compared with real deployment performance.

This is the test that would make the work compelling.

---

# 21. Second Killer Experiment: Predict the Whole Distribution Shift

The predictor outputs:

\[
\hat P_{C+x}(T\mid q)
\]

before deployment.

After deployment we obtain:

\[
P_{C+x}(T\mid q)
\]

Measure:

\[
JS(
\hat P,
P
)
\]

and:

\[
TopK\ overlap
\]

This demonstrates that the model isn't merely predicting whether performance drops; it predicts **where the selection probability moves**.

---

# 22. Third Killer Experiment: Tool-Addition Ranking

Give the system 100 candidate tools:

```text
x1
x2
...
x100
```

Predict the top 10 most damaging additions.

Then actually test all 100.

Measure:

\[
Recall@10
\]

of the truly most damaging tools.

A strong result would be:

```text
10 predicted risky tools

8/10 actually in the worst 10
```

This is directly useful for a production tool registry.

---

# 23. Fourth Killer Experiment: Safe-Catalog Construction

Given:

```text
200 candidate tools
```

select a subset that maximizes capability coverage subject to:

\[
PredictedInterference \le \tau
\]

Then compare:

### Baseline

Semantic pruning.

### Proposed

Predictive interference-aware pruning.

Measure:

```text
capability coverage
task success
catalog size
tool tokens
interference
```

This turns the predictive model into an optimization system.

---

# 24. The Strongest Possible Result

A compelling result would look like:

```text
Predictor performance on unseen tools:

MAE accuracy delta:     0.008
Spearman:               0.82
Risk ranking Recall@10: 0.80

Catalog construction:

Coverage:               97%
Tools exposed:           42% fewer
Task accuracy:           -0.3 pp
Tool-selection failures: 38% lower
```

Numbers above are targets/examples, not claims.

---

# 25. Phase-Transition Hypothesis

A deeper scientific question:

Does interference have a critical density?

Let:

\[
\rho =
\frac{\text{behaviorally interacting tool pairs}}
{\text{all possible tool pairs}}
\]

Hypothesis:

\[
Performance \approx f(\rho)
\]

with potentially a nonlinear transition:

```text
Accuracy
1.0 |────────────────
    |              ────
0.8 |                  ───
    |                     ───
0.6 |                        ────
    +---------------------------->
              Interference Density
```

If this appears consistently across models, it may provide a genuinely useful **tool-space scaling law**.

---

# 26. Model Dependence

The predictor should explicitly include model \(M\).

Why?

Because:

\[
I_{ij}^{GPT}
\neq
I_{ij}^{Qwen}
\]

is entirely plausible.

Therefore a tool catalog is not inherently safe or unsafe.

It is:

\[
Risk(C,M)
\]

The same tool could be low-risk for one model and high-risk for another.

This creates the possibility of:

> **model-specific tool compatibility certification.**

---

# 27. Task Distribution Dependence

Risk also depends on \(Q\).

A tool that is dangerous for:

```text
customer support
```

may be harmless for:

```text
coding
```

Therefore:

\[
Risk=Risk(C,M,Q)
\]

This means evaluation must include task-distribution shift.

---

# 28. Distribution Shift Experiment

Train predictor on:

```text
Q_train
```

Test on:

```text
Q_test
```

with different:

- domains;
- frequency;
- query complexity;
- task composition;
- tool usage patterns.

The question:

> Does the predictor learn general tool interference or merely memorize workload correlations?

---

# 29. Why This Is Hard

There are at least four serious challenges.

## 1. Observational confounding

Historical tool catalogs may already have been curated in response to failures.

## 2. Higher-order interactions

Pairwise models may fail.

## 3. Model-specific behavior

The same tool may affect different models differently.

## 4. Task-distribution dependence

There may be no universal interference score.

These are research problems, not implementation details.

---

# 30. Preventing the "Just a Classifier" Criticism

The work should not be:

```text
Features → XGBoost → predicted accuracy
```

only.

The contribution should include:

### Structural intervention model

\[
\hat I(t|C,M,Q)
\]

### Distribution-shift prediction

\[
\hat P_{C+t}(T|q)
\]

### Interaction decomposition

\[
pairwise + higher-order
\]

### Uncertainty

\[
P(
|\Delta-\hat{\Delta}|<\epsilon
)
\]

### Deployment decision

\[
Expose(t)
\iff
Risk(t)<threshold
\]

That forms a coherent systems method.

---

# 31. Comparison With Existing Approaches

| Approach | What it does | What PTIM adds |
|---|---|---|
| Tool-space interference | Measures interference | Predict before deployment |
| Tool filtering | Removes unnecessary tools | Quantify damage of candidate additions |
| Tool discovery | Selects relevant tools | Predict catalog-wide risk |
| Tool compatibility | Scores/selects compatible tools | Forecast behavioral regression |
| Causal tool filtering | Estimates effects of exposure | Pre-deployment generalization |
| Tool-set benchmarks | Measure observed performance | Predict unseen changes |
| Tool evolution benchmarks | Evaluate versions | Forecast future regressions |

The distinctions need to be demonstrated experimentally, not merely asserted.

---

# 32. Potential Contribution to AI Engineering

A tool registry could eventually implement:

```python
risk = predictor.predict(
    model=model,
    current_catalog=catalog,
    candidate_tool=new_tool,
    workload=workload
)

if risk.expected_accuracy_delta < -0.02:
    reject()
elif risk.confidence < 0.8:
    quarantine_for_online_test()
else:
    approve()
```

That makes the research directly operational.

---

# 33. Potential Public Artifact

Repository:

```text
ptim/
├── datasets/
├── catalog_generator/
├── mutation_engine/
├── intervention_runner/
├── predictor/
├── interaction_models/
├── uncertainty/
├── evaluation/
├── examples/
└── dashboard/
```

CLI:

```bash
ptim predict \
  --model model_A \
  --catalog catalog_42 \
  --candidate tool_981 \
  --workload enterprise_support
```

Output:

```text
Predicted accuracy delta:   -1.9 pp
90% interval:               [-2.7, -1.1]

Risk level:                 MEDIUM

Main competitors:
  search_orders      0.31
  lookup_payments    0.22

Expected probability shift:
  search_orders      +0.07
  lookup_payments    +0.04
  correct tool       -0.09
```

---

# 34. Falsification Criteria

The hypothesis should be abandoned if:

1. The predictor cannot generalize to unseen tools.
2. Simple semantic similarity predicts the same thing equally well.
3. Tool metadata alone has insufficient predictive signal.
4. Higher-order interactions make prediction effectively impossible.
5. Different workloads produce completely unrelated interference.
6. The model's tool-selection distribution is too unstable to predict.
7. The predicted risk has no relationship with actual deployment regression.

A failed result is valuable because it would establish that tool interference is fundamentally too context-dependent for reliable pre-deployment prediction.

---

# 35. What Would Count as a Real Research Result?

A strong result is not merely:

> "Our predictor gets 90% accuracy."

The key result should be:

> **A predictor trained on historical tool additions can accurately rank or estimate the risk of completely unseen future tool additions on unseen catalogs and workloads.**

That would demonstrate generalization of a behavioral law.

---

# 36. Novelty Status After Preliminary Review

### We should claim:

> **Potentially novel predictive formulation.**

### We should not claim:

> **First work on tool interference.**

### We should not claim:

> **First work on tool interactions.**

### We should not claim:

> **First causal tool-selection study.**

The potentially novel contribution is:

\[
\boxed{
\text{pre-deployment prediction of marginal agent degradation from an unseen tool addition}
}
\]

plus, optionally:

\[
\boxed{
\text{prediction of the resulting tool-selection distribution shift}
}
\]

and:

\[
\boxed{
\text{a structural interaction model that explains the prediction}
}
\]

---

# 37. Prior-Art Summary

Important neighboring research includes:

- **Tool-space interference** — establishes that tool exposure itself can degrade agent behavior.
- **HYSET** — models tool-set compatibility and cardinality-specific interactions.
- **CMTF / GIST-CMTF** — uses causal intervention and filtering to reduce unnecessary tool exposure.
- **ToolScope** — merges/prunes redundant tool capabilities.
- **Semantic Tool Discovery** — retrieves a small tool subset from large MCP catalogs.
- **MCPEvol-Bench** — evaluates agents across evolving MCP server/tool configurations.
- **EvolveTool-Bench** — studies evolving tool libraries and regression.
- **RobustBench-TC** — studies tool-interface perturbations including descriptions and schemas.

These constrain the novelty claim but do not, from the current search, directly establish the exact **pre-deployment unseen-tool interference prediction problem**.

---

# 38. Recommended First Implementation

Do not start with thousands of tools.

Start with:

```text
50 tools
20 tasks families
5 models
100 candidate additions
10 random seeds
```

Create:

```text
baseline catalogs
candidate additions
measured interventions
```

Fit simple baselines:

1. semantic similarity;
2. lexical overlap;
3. schema overlap;
4. linear regression;
5. gradient boosting;
6. graph model.

The goal of the first prototype is to answer:

> **Is there actually predictable signal?**

If a simple baseline already predicts interference extremely well, that is itself a result, and a complex model may be unnecessary.

---

# 39. Experimental Order

### Experiment A

Can we predict the sign?

\[
\Delta L > 0
\quad\text{or}\quad
\Delta L < 0
\]

### Experiment B

Can we rank risky tools?

\[
Recall@K
\]

### Experiment C

Can we predict magnitude?

\[
MAE / RMSE
\]

### Experiment D

Can we predict probability redistribution?

\[
JS(\hat P,P)
\]

### Experiment E

Can the model generalize to unseen tool families?

### Experiment F

Can it generalize across models?

### Experiment G

Can it predict future catalog failures before deployment?

Only after passing these should the project scale.

---

# 40. Final Research Thesis

> **Tool exposure should be treated as a controllable intervention on an LLM agent's decision policy, and the marginal behavioral cost of a new tool should be predictable before deployment.**

The research objective is:

\[
\boxed{
\hat{\Delta L}(C,t,M,Q)
\approx
L(C\cup\{t\},M,Q)-L(C,M,Q)
}
\]

without executing the target workload after adding \(t\).

The stronger objective is:

\[
\boxed{
\hat P_{C+t}(T|q,M)
\approx
P_{C+t}(T|q,M)
}
\]

which predicts the actual movement of the agent's decision policy.

---

# 41. Final Assessment

### Novelty confidence: **moderate, not proven**

I would currently rate the research direction:

**7/10 for novelty potential**

not:

**10/10 proven originality.**

The broad phenomenon is established.

The predictive formulation appears to be the least-covered part of the problem found in the current search.

The decisive evidence will come from a **zero-shot intervention experiment** demonstrating that an interference model can predict the impact of an entirely unseen tool addition on an unseen catalog/workload.

If that experiment succeeds robustly, the contribution becomes considerably stronger than another tool benchmark:

> **a predictive safety layer for evolving agent tool catalogs.**

---

# 42. One-Sentence Version

> **PTIM predicts how much an unseen tool will change an LLM agent's tool-selection behavior and task performance before the tool is exposed, using a structural model of tool–tool interactions rather than waiting for production failures.**
