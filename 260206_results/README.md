# 260206_results — Experiment Summary & Tables for Paper (A*)

This document summarizes the **environment (env)**, **seeds**, and **detailed evaluation** from the `260206_results` folder for use when writing the paper (targeting A* ranking).

---

## 1. Environment and Configuration

### 1.1 Environment Variables in Use

| Variable | Value | Description |
|----------|-------|-------------|
| **OPENAI_API_KEY** | (set) | OpenAI API key |
| **OPENAI_MODEL** | `gpt-4o-mini` | LLM model for all agents |
| **USE_LLM_EVIDENCE_EVAL** | `1` | Enable LLM-based evidence scoring (per-sentence then aggregate) combined with string match |
| **NUM_TASKS** | `500` | Number of tasks (claims) per milestone |
| **NUM_SAMPLES** | `500` | Number of FEVER samples loaded (pool ≥ NUM_TASKS) |
| **SEEDS** | `42` | Multi-seed; this folder contains results for seeds **42** and **123** (M2), **42** (M3, M4) |

### 1.2 Payoff and Budget (from result files)

- **Payoff**: \( U = \text{quality} - \lambda\,\text{cost} - \mu\,\text{penalty} \)
  - \(\lambda = 0.01\), \(\mu = 0.5\)
  - token_cost_per_1k = 0.0001, tool_call_cost = 0.01
- **Budget (M3)**: max_tokens_per_task = 2000, max_calls_per_task = 10 (same for P1 and baselines)

### 1.3 Dataset

- **FEVER** (Fact Extraction and VERification): claim + label (Supported / Refuted / Not Enough Info) + evidence.
- Evidence evaluation: string/semantic match + LLM-based per-sentence scoring (because `USE_LLM_EVIDENCE_EVAL=1`).

---

## 2. Seeds and Result Files

| Milestone | Description | Seeds in folder | Main files |
|-----------|-------------|----------------|------------|
| **M2** | Deviation Suite (P1, 6 deviation types + IRI) | 42, 123 | `milestone2/seed42.json`, `seed123.json`, `deviation_suite_results.json` |
| **M3** | Baseline (P1 vs Self-Consistency K=5, Self-Refine R=2) | 42 | `milestone3/seed42.json`, `baseline_comparison.json` |
| **M4** | Protocol progression (P1 vs P2 vs P3) | 42 | `milestone4/protocol_comparison_seed42.json`, `protocol_comparison.json` |

**Note**: M3 and M4 currently have results for seed 42 only. To report **mean ± std** for M3/M4 in the paper, run seeds 123 and 456 and aggregate.

---

## 3. Tables for Paper (A*)

### 3.1 Milestone 2 — Deviation Suite (P1 Evidence-First)

**Source**: `milestone2/seed42.json`, `milestone2/seed123.json`.  
Tasks: seed42 = 500, seed123 = 492. IRI for both seeds = **0.0**.

#### Table 1: Deviation Gain (DG) by deviation type (mean ± std over seeds 42, 123)

| Deviation       | DG (mean ± std)   | % DG > 0 (mean) | Assessment     |
|----------------|-------------------|------------------|----------------|
| no_evidence    | −0.59 ± 0.01      | ~27%             | Very effective |
| persuasion_only | −0.61 ± 0.02    | ~27%             | Very effective |
| lie           | −0.18 ± 0.02      | ~18%             | Effective      |
| withhold      | −0.13 ± 0.03      | ~17%             | Effective      |
| low_effort    | −0.10 ± 0.02      | ~25%             | Weakest        |
| **IRI**       | **0.00**          | —                | Optimal        |

*(Exact values: no_evidence DG ≈ −0.579 (s42), −0.606 (s123); lie −0.166, −0.202; withhold −0.147, −0.111; persuasion_only −0.592, −0.622; low_effort −0.088, −0.115.)*

#### Honest (P1) — 2 seeds

| Metric                 | Seed 42 | Seed 123 | Mean ± Std (approx) |
|------------------------|---------|----------|----------------------|
| Accuracy               | 0.368   | 0.376    | 0.37 ± 0.01          |
| Evidence compliance    | 1.0     | 1.0      | 1.00                 |
| Evidence match score   | 0.682   | 0.685    | 0.68 ± 0.00          |
| Mean payoff           | 0.287   | 0.298    | 0.29 ± 0.01          |

**Claim for paper**: DG < 0 for all deviations; IRI = 0 → no deviation is profitable on average; protocol P1 makes truthful, evidence-backed behavior incentive-compatible.

---

### 3.2 Milestone 3 — Baseline Comparison (seed 42)

**Source**: `milestone3/seed42.json`, `milestone3/baseline_comparison.json`.  
Same budget: 2000 tokens/task, 10 calls/task.

#### Table 2: P1 vs Self-Consistency vs Self-Refine

| Method                | Accuracy | Evidence compliance | Evidence match | Mean payoff |
|------------------------|----------|----------------------|----------------|-------------|
| Self-Refine R=2        | **0.488**| 0                    | 0              | −0.14       |
| Self-Consistency K=5   | 0.474    | 0                    | 0              | −0.16       |
| **P1 Evidence-First** | 0.352    | **1.00**             | **0.68**      | **0.27**    |

**Rankings (from file)**: Accuracy — Self-Refine > Self-Consistency > P1; Evidence compliance — P1 > Self-Consistency = Self-Refine; Payoff — P1 > Self-Refine > Self-Consistency.

**Claim for paper**: P1 trails baselines by ~12 points in accuracy but is the **only** method with evidence compliance and evidence match; higher payoff because baselines are penalized for lacking evidence. Suitable when the goal is **truthful, evidence-backed** output rather than maximizing accuracy alone.

---

### 3.3 Milestone 4 — Protocol Comparison P1 vs P2 vs P3 (seed 42)

**Source**: `milestone4/protocol_comparison_seed42.json`.  
Deviation types: honest, lie, withhold, persuasion_only.

#### Table 3: Honest metrics by protocol

| Protocol         | Accuracy | Evidence compliance | Evidence match | Mean payoff |
|------------------|----------|----------------------|----------------|-------------|
| P1 Evidence-First | 0.346   | 1.00                 | 0.68           | 0.26        |
| P2 Cross-Exam    | **0.428** | 1.00               | 0.71           | **0.36**    |
| P3 Slashing      | 0.414    | 1.00                 | 0.70           | 0.34        |

#### Table 4: Deviation Gain by protocol (seed 42)

| Deviation       | P1 DG   | P2 DG   | P3 DG   |
|-----------------|---------|---------|---------|
| lie             | −0.16   | −0.16   | −0.14   |
| withhold        | −0.06   | −0.10   | −0.08   |
| persuasion_only | −0.56   | −0.60   | −0.60   |

**IRI**: P1 = P2 = P3 = **0.0** (in seed 42 file).

**Claim for paper**: P2 and P3 improve accuracy and payoff over P1 when honest; DG remains negative for all deviations → progression P1 → P2 → P3 increases quality while preserving incentive robustness.

---

## 4. Detailed Evaluation (for A* Paper)

### 4.1 Game-theoretic metrics

- **Deviation Gain (DG)**  
  DG = E[payoff | deviation] − E[payoff | honest].  
  DG < 0: deviation is disadvantageous → protocol is effective against that deviation.

- **Incentive Robustness Index (IRI)**  
  IRI = (1/|D|) Σ_d max(DG(d), 0).  
  IRI = 0: no deviation is profitable on average; lower is better.

- **% DG > 0**  
  Fraction of episodes where deviation was beneficial; lower indicates a more stable protocol.

### 4.2 Task-level metrics

- **Accuracy**: fraction of correct FEVER labels.
- **Evidence compliance**: fraction of episodes with evidence provided in the correct format.
- **Evidence match score**: similarity of provided evidence to ground truth (0–1); with `USE_LLM_EVIDENCE_EVAL=1` this combines string match + LLM scoring.

### 4.3 Payoff

- **Mean payoff**: average U = quality − λ·cost − μ·penalty over episodes.  
  P1 has positive mean payoff due to evidence; baselines are penalized for lacking evidence, hence negative payoff.

### 4.4 Strengths for paper

1. **IRI = 0** (M2): no deviation is profitable on average.
2. **DG < 0** for all deviation types in P1 (and P2, P3 in M4).
3. **P1 is the only** method with evidence compliance and evidence match vs Self-Consistency/Self-Refine.
4. **P2, P3** improve accuracy and payoff over P1 when honest.

### 4.5 Limitations / Additions for A*

1. **Multi-seed for M3, M4**: Currently only seed 42. Run seeds 123 and 456 for M3 and M4, then report mean ± std (accuracy, payoff, DG, IRI) in the paper.
2. **P1 accuracy lower than baselines**: Clearly state the trade-off (accuracy vs evidence/truthfulness) and positioning (evidence-based decision vs pure accuracy).
3. **Low_effort and withhold**: Smaller DG (≈ −0.10, −0.06 for P1); can be discussed in Discussion (e.g., cross-exam/slashing in P2/P3 helps reduce withhold DG).

---

## 5. Env + Seed Summary (copy to paper / appendix)

- **Model**: OpenAI `gpt-4o-mini`.  
- **Evidence evaluation**: String match + LLM per-sentence scoring (`USE_LLM_EVIDENCE_EVAL=1`).  
- **Tasks**: 500 (M2: 500/492 by seed; M3, M4: 500).  
- **Dataset**: FEVER.  
- **Seeds**: 42, 123 (M2); 42 (M3, M4).  
- **Payoff**: λ = 0.01, μ = 0.5; M3 budget: 2000 tokens, 10 calls per task.

---

## 6. Quick File Reference

| File | Content |
|------|---------|
| `milestone2/seed42.json` | M2 full seed 42 (metrics_by_type, deviation_gains, IRI) |
| `milestone2/seed123.json` | M2 full seed 123 |
| `milestone3/seed42.json`, `baseline_comparison.json` | M3 seed 42 |
| `milestone4/protocol_comparison_seed42.json` | M4 P1/P2/P3 seed 42 |

Use the tables in §3 directly when writing Results and cross-check with the JSON files above.
