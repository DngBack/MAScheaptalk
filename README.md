# MAS Cheap Talk: Communication Protocols for LLM Multi-Agent Systems

Game-theoretic protocols for truthful communication in LLM-based multi-agent systems: **Evidence-First (P1)**, **Cross-Examination (P2)**, and **Reputation/Slashing (P3)** on the FEVER benchmark.

---

## Overview

This project implements **communication protocols** so that truthful, evidence-backed communication becomes **incentive-compatible** and deviations (lying, withholding evidence, persuasion-only) become **disadvantageous** (negative Deviation Gain). It includes:

| Milestone | Description |
|-----------|-------------|
| **Milestone 1** | P1 Evidence-First + FEVER (CLI, config YAML). |
| **Milestone 2** | Deviation Suite — all deviation types (honest, no_evidence, lie, withhold, persuasion_only, low_effort) and IRI. |
| **Milestone 3** | Baseline comparison — P1 vs Self-Consistency and Self-Refine (same budget). |
| **Milestone 4** | Protocol progression — P1 vs P2 vs P3. |

**Evidence evaluation**: String/semantic match of provided evidence vs ground truth; optional **LLM-based per-sentence scoring** (set `USE_LLM_EVIDENCE_EVAL=1` in `.env`).

---

## Architecture

Clean Architecture with four layers:

```
src/
├── domain/          # Entities (Task, Episode, Message, Evidence, Reputation), value objects, ports
├── application/     # Use cases, protocols (P1, P2, P3), baselines, scoring
├── infrastructure/  # FEVER dataset, verifiers (incl. LLM evidence evaluator), storage, LLM, AutoGen
└── interfaces/      # CLI, configs (YAML)
```

---

## Installation

### Prerequisites

- **Python 3.11+** (3.11 recommended)
- **pip**

### Step-by-step setup

1. **Clone and enter the project**
   ```bash
   cd /path/to/MAScheaptalk
   ```

2. **Create and activate virtual environment**
   ```bash
   python3.11 -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and set at least:
   - `OPENAI_API_KEY=sk-your-key-here` (required for real LLM runs)
   - Optionally: `NUM_TASKS`, `NUM_SAMPLES`, `SEED`, `SEEDS`, `USE_LLM_EVIDENCE_EVAL`, `OPENAI_MODEL` (see table below).

5. **Create results directories** (optional; scripts may create them)
   ```bash
   mkdir -p results/milestone2 results/milestone3 results/milestone4
   ```

6. **Validate setup**
   ```bash
   python validate_setup.py
   ```
   This checks imports, loads a small FEVER sample, and initializes the P1 protocol. Fix any reported errors before running experiments.

---

## Environment variables (.env)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes (for real runs) | — | OpenAI API key for LLM calls. Get from https://platform.openai.com/api-keys |
| `NUM_TASKS` | No | 500 | Number of tasks to run per milestone (M2, M3, M4). |
| `NUM_SAMPLES` | No | 500 | Number of FEVER samples to load; should be ≥ NUM_TASKS. |
| `SEED` | No | 42 | Random seed for reproducibility (single run). |
| `SEEDS` | No | — | Multi-seed in one run: e.g. `42,123,456`. Runs each seed then aggregates mean±std. |
| `USE_LLM_EVIDENCE_EVAL` | No | 0 | Set to `1`, `true`, or `yes` to add LLM-based evidence scoring (per-sentence then aggregate). |
| `OPENAI_MODEL` | No | gpt-4o-mini | Model name (e.g. gpt-4o-mini, gpt-4o). |

---

## Tasks, samples, and episodes (detailed)

Understanding these three terms is essential for configuring runs and reading results.

### Sample

- **Sample** = **one row** loaded from the FEVER dataset (HuggingFace).
- Each row contains: a **claim** (e.g. “The Beatles formed in 1960”), a **label** (SUPPORTED / REFUTED / NOT ENOUGH INFO), and **evidence** (sentences that support or refute the claim).
- **NUM_SAMPLES** = how many such rows to load from FEVER (e.g. 500). This is the “pool” of data you have.

### Task

- **Task** = **one claim** (and its label + evidence) **used as a single unit of experiment**.
- In code, a `Task` has: `task_id`, `claim`, `label`, `evidence`, `metadata`. It comes from one FEVER row.
- **NUM_TASKS** = how many of the loaded samples you actually **run** in the experiment. You should have **NUM_TASKS ≤ NUM_SAMPLES** (typically equal: use all 500 loaded rows as 500 tasks).

So: **one sample becomes one task** when we use it in the run. “Task” emphasizes “one claim we evaluate”; “sample” emphasizes “one row we loaded from the dataset.”

### Episode

- **Episode** = **one simulation** of the protocol on **one task** under **one condition** (e.g. one deviation type or one baseline).
- For example: same claim (same task), but we run it once with **honest** behavior and once with **lie** → that gives **2 episodes** for that task.
- In Milestone 2 (deviation suite): for each task we run **6 episodes** (honest, no_evidence, lie, withhold, persuasion_only, low_effort). So **500 tasks × 6 = 3,000 episodes**.
- In Milestone 4 (protocols): for each task we run **P1, P2, P3** and several deviation types → many episodes per task.

### Summary diagram

```
FEVER dataset (HuggingFace)
        │
        ▼  load NUM_SAMPLES rows (e.g. 500)
   ┌────────────┐
   │  Samples   │  ← each row = 1 claim + label + evidence
   └────────────┘
        │
        ▼  use first NUM_TASKS as experiment units (e.g. 500)
   ┌────────────┐
   │   Tasks    │  ← 1 task = 1 claim (+ label + evidence) we evaluate
   └────────────┘
        │
        ▼  for each task, run protocol with different deviation types / baselines / protocols
   ┌────────────┐
   │  Episodes  │  ← 1 episode = 1 run of 1 task with 1 deviation type (or 1 protocol)
   └────────────┘
```

### Example with numbers

- **NUM_SAMPLES=500**, **NUM_TASKS=500**: Load 500 FEVER rows, use all 500 as tasks.
- **Milestone 2**: 500 tasks × 6 deviation types → **3,000 episodes** (each episode = one Sender–Receiver conversation for one claim under one deviation).
- **Milestone 3**: 500 tasks × 3 methods (P1, Self-Consistency, Self-Refine) → **1,500 episodes**.
- **Milestone 4**: 500 tasks × 3 protocols × 4 deviation types → **6,000 episodes**.

So when you set **NUM_TASKS=10** for a quick test, you are running the experiment on **10 claims**; each claim may be run multiple times (different episodes) depending on the milestone.

---

## Usage

### 1. Quick test (few tasks, ~minutes)

Before a full run, verify the pipeline with a small number of tasks.

In `.env` set:

```env
NUM_TASKS=10
NUM_SAMPLES=10
SEED=42
```

Then run all milestones:

```bash
source .venv/bin/activate
python run_all_milestones.py
```

Press Enter when prompted. Results go to `results/milestone2/`, `results/milestone3/`, `results/milestone4/`. If this completes without errors, you can increase `NUM_TASKS` and `NUM_SAMPLES` for submission runs.

---

### 2. Submission run (500 tasks, one seed)

In `.env`:

```env
OPENAI_API_KEY=sk-your-key
NUM_TASKS=500
NUM_SAMPLES=500
SEED=42
```

Run:

```bash
python run_all_milestones.py
```

This runs Milestone 2, 3, and 4 with 500 tasks and seed 42. Outputs:

- `results/milestone2/deviation_suite_results.json`
- `results/milestone3/baseline_comparison.json`
- `results/milestone4/protocol_comparison.json`

---

### 3. Multi-seed in one run (mean ± std for paper)

In `.env` add (and keep `NUM_TASKS`, `NUM_SAMPLES` as desired):

```env
SEEDS=42,123,456
```

Run:

```bash
python run_all_milestones.py
```

The script will:

1. Run M2 → M3 → M4 with **SEED=42**, then copy results to `seed42.json`, `protocol_comparison_seed42.json`, etc.
2. Repeat for **SEED=123**, **SEED=456**.
3. Call the aggregate script and write **`results/submission_multi_seed_summary.json`** (mean ± std for IRI, accuracy, payoff, evidence_match_score, DG).

Use this file for tables in the paper. If you prefer to run seeds manually and then aggregate, see [SUBMISSION_RUN.md](SUBMISSION_RUN.md).

---

### 4. Run individual milestones

Each script reads `NUM_TASKS`, `NUM_SAMPLES`, `SEED` from `.env` (defaults 500, 500, 42).

```bash
python run_milestone2_deviation.py    # Deviation Suite (all deviation types, IRI)
python run_milestone3_baselines.py    # P1 vs Self-Consistency, Self-Refine
python run_milestone4_protocols.py    # P1 vs P2 vs P3
```

---

### 5. Milestone 1 (CLI + YAML config)

Run the Evidence-First protocol via the CLI with a YAML config:

```bash
python src/interfaces/cli/main.py --config src/interfaces/configs/milestone1.yaml
```

Override from command line:

```bash
python src/interfaces/cli/main.py --config src/interfaces/configs/milestone1.yaml --num-tasks 20 --output results/m1_test.jsonl
```

---

### 6. Debug evidence verification

Run one episode and print verifier debug info (evidence_match_score, num_gt_sentences, etc.):

```bash
python scripts/debug_evidence_verifier.py
```

With LLM evidence scoring:

```bash
python scripts/debug_evidence_verifier.py --llm-eval
```

---

### 7. Aggregate multi-seed results manually

If you ran multiple seeds by hand (e.g. changing `SEED` and re-running), place the per-seed result files in the expected locations (e.g. `results/milestone2/seed42.json`, `seed123.json`, ...), then run:

```bash
python scripts/aggregate_multi_seed_results.py
```

This produces `results/submission_multi_seed_summary.json` with mean ± std for key metrics.

---

## Key concepts

### Protocols

- **P1 Evidence-First**: Claim → Evidence → Decision. Sender must provide evidence; Receiver checks evidence before deciding.
- **P2 Cross-Examination**: P1 + a cross-examination phase (Receiver asks probing questions, Sender answers).
- **P3 Slashing**: P2 + reputation/slashing (low reputation increases cost and triggers verification).

### Deviation Gain (DG)

- **DG** = mean(payoff when deviating) − mean(payoff when honest).
- **DG < 0**: deviation is disadvantageous → protocol is effective.
- **DG > 0**: deviation is advantageous → protocol needs improvement.

### Incentive Robustness Index (IRI)

- IRI aggregates how much deviations “pay off” (e.g. mean of max(DG, 0) over deviation types). **Lower is better**; IRI = 0 means no deviation is profitable.

### Payoff

- **Payoff** = quality − λ×cost − μ×penalty.  
- **quality**: weighted combination of label accuracy, evidence match score, and evidence compliance.

### Evidence evaluation

- **evidence_compliance**: whether the agent provided evidence (binary).
- **evidence_match_score**: similarity of provided evidence to ground truth (string overlap or optional LLM scoring).  
- Optional: set `USE_LLM_EVIDENCE_EVAL=1` to score each evidence sentence with an LLM and combine with string match (e.g. 0.5/0.5 weights).

---

## Metrics and results

### Task-level

- **Accuracy**: fraction of episodes with correct FEVER label.
- **Evidence compliance**: fraction of episodes with evidence provided.
- **Evidence match score**: average evidence similarity to ground truth (0–1).

### Game-theoretic

- **Deviation Gain (DG)** per deviation type.
- **% DG > 0**: fraction of episodes where deviation was beneficial.
- **IRI**: Incentive Robustness Index.

### Result files

| File | Content |
|------|--------|
| `results/milestone2/deviation_suite_results.json` | Metrics by deviation type, deviation_gains, IRI. |
| `results/milestone3/baseline_comparison.json` | P1 vs Self-Consistency, Self-Refine (accuracy, payoff, evidence). |
| `results/milestone4/protocol_comparison.json` | P1, P2, P3 metrics and IRI. |
| `results/submission_multi_seed_summary.json` | Mean ± std across seeds (when using `SEEDS` or manual aggregation). |

---

## Submission run (paper)

For a full run suitable for paper submission (500 tasks, optional multi-seed):

1. Set in `.env`: `NUM_TASKS=500`, `NUM_SAMPLES=500`, and optionally `SEEDS=42,123,456`.
2. Run: `python run_all_milestones.py`.
3. Use `results/submission_multi_seed_summary.json` for tables (if multi-seed).

Detailed steps, time/cost estimates, and manual multi-seed options: **[SUBMISSION_RUN.md](SUBMISSION_RUN.md)**.

---

## Recommended configuration and metrics for paper

To get **publication-ready** results, use the following setup and report the listed metrics.

### Recommended run configuration

| Parameter | Recommended value | Reason |
|-----------|-------------------|--------|
| **NUM_TASKS** | **500** | Enough for statistical significance; standard for FEVER-style experiments. |
| **NUM_SAMPLES** | **500** | Same as NUM_TASKS (use all loaded samples as tasks). |
| **SEEDS** | **42,123,456** (or at least 3 seeds) | Report **mean ± std** for robustness; reviewers expect variance. |
| **SEED** | 42 (if single run) | Reproducibility when not using multi-seed. |
| **USE_LLM_EVIDENCE_EVAL** | 0 or 1 | 0 = string match only (faster/cheaper); 1 = add LLM evidence scoring. |
| **OPENAI_MODEL** | gpt-4o-mini | Balance cost vs quality; use gpt-4o if budget allows. |

**Example `.env` for paper:**

```env
OPENAI_API_KEY=sk-your-key
NUM_TASKS=500
NUM_SAMPLES=500
SEEDS=42,123,456
SEED=42
# USE_LLM_EVIDENCE_EVAL=0
# OPENAI_MODEL=gpt-4o-mini
```

Then run: `python run_all_milestones.py`. Use **`results/submission_multi_seed_summary.json`** for tables (mean ± std).

---

### Metrics to report in the paper

#### From Milestone 2 (Deviation Suite)

- **IRI** (Incentive Robustness Index): lower is better; IRI = 0 means no deviation is profitable.
- **Deviation Gain (DG)** per deviation type: **DG &lt; 0** means the protocol penalizes that deviation.
- **% DG &gt; 0**: fraction of episodes where deviation was beneficial; lower is better.

**Table 1 (example):** Deviation Gain by type (mean ± std over seeds).

| Deviation      | DG (mean ± std) | % DG &gt; 0 | Interpretation   |
|----------------|------------------|-------------|-------------------|
| no_evidence    | −0.35 ± 0.02     | 30%         | Effective         |
| lie            | −0.31 ± 0.03     | 10%         | Effective         |
| withhold       | −0.13 ± 0.02     | 20%         | Effective         |
| persuasion_only| −0.50 ± 0.04     | 5%          | Very effective    |
| low_effort     | −0.08 ± 0.02     | 25%         | Moderate          |
| **IRI**        | **0.03 ± 0.01**  | —           | Overall robustness |

Data source: `submission_multi_seed_summary.json` → `milestone2.deviation_gains`, `milestone2.mean.iri` / `std.iri`.

---

#### From Milestone 3 (Baseline comparison)

- **Accuracy**: fraction of correct FEVER labels.
- **Evidence compliance**: fraction of episodes with evidence provided (P1 should be high; baselines typically 0).
- **Evidence match score**: 0–1, relevance of evidence to ground truth.
- **Mean payoff**: quality − cost − penalty.

**Table 2 (example):** P1 vs baselines (mean ± std).

| Method              | Accuracy   | Evidence compliance | Evidence match | Mean payoff |
|---------------------|------------|----------------------|----------------|-------------|
| P1 Evidence-First   | 0.68 ± 0.02 | **0.92 ± 0.01**     | 0.65 ± 0.03    | 0.12 ± 0.05 |
| Self-Consistency K=5| **0.71 ± 0.02** | 0.00            | 0.00           | 0.08 ± 0.06 |
| Self-Refine R=2     | 0.69 ± 0.02 | 0.00                | 0.00           | 0.05 ± 0.05 |

**Claim for paper:** P1 is competitive in accuracy (within a few % of best baseline) while being the only method with high evidence compliance and evidence match.

Data source: `submission_multi_seed_summary.json` → `milestone3.methods`.

---

#### From Milestone 4 (Protocol progression)

- **IRI** per protocol: P1, P2, P3. Expect **IRI(P3) ≤ IRI(P2) ≤ IRI(P1)** (improvement with stricter protocols).
- **Honest metrics** per protocol: accuracy, evidence_compliance, evidence_match_score, mean_payoff.

**Table 3 (example):** Protocol comparison (mean ± std).

| Protocol   | IRI (mean ± std) | Honest accuracy | Honest evidence compliance |
|------------|-------------------|------------------|-----------------------------|
| P1         | 0.15 ± 0.02       | 0.68 ± 0.02      | 0.92 ± 0.01                |
| P2         | 0.08 ± 0.01       | 0.70 ± 0.02      | 0.94 ± 0.01                |
| P3         | **0.03 ± 0.01**   | 0.69 ± 0.02      | 0.95 ± 0.01                |

**Claim for paper:** IRI decreases from P1 → P2 → P3, showing that cross-examination and reputation/slashing further reduce the incentive to deviate.

Data source: `submission_multi_seed_summary.json` → `milestone4.protocols`.

---

### What “good” looks like (interpretation)

| Metric / result | Good for paper |
|-----------------|----------------|
| **DG &lt; 0** for all (or most) deviation types | Protocol makes deviation unprofitable. |
| **IRI** small (e.g. &lt; 0.1) | Few or no deviations are beneficial on average. |
| **% DG &gt; 0** low (e.g. &lt; 25%) | Deviation rarely pays off. |
| **P1 evidence compliance** &gt; 0.9 | Evidence-First protocol is followed. |
| **P1 accuracy** within ~5% of best baseline (M3) | No large accuracy trade-off for evidence. |
| **IRI(P3) &lt; IRI(P2) &lt; IRI(P1)** (M4) | Protocol progression improves incentive robustness. |

---

### Single-seed vs multi-seed

- **Single seed (e.g. SEED=42):** Use `results/milestone2/deviation_suite_results.json`, `baseline_comparison.json`, `protocol_comparison.json` directly. Report metrics without std (or “one run”).
- **Multi-seed (SEEDS=42,123,456):** Use `results/submission_multi_seed_summary.json`. Report **mean ± std** in tables; stronger for review.

---

## Project structure

```
MAScheaptalk/
├── run_all_milestones.py      # Run M2 + M3 + M4 (single or multi-seed)
├── run_milestone2_deviation.py
├── run_milestone3_baselines.py
├── run_milestone4_protocols.py
├── validate_setup.py           # Validate installation and imports
├── src/
│   ├── domain/
│   │   ├── entities/          # Task, Episode, Message, Evidence, Reputation
│   │   ├── value_objects/     # AgentRole, FEVERLabel
│   │   └── ports/             # DatasetRepository, LLMClient, Verifier, Storage
│   ├── application/
│   │   ├── protocols/         # P1, P2, P3, deviation_policies
│   │   ├── baselines/         # SelfConsistency, SelfRefine
│   │   ├── scoring/           # FEVERScoring, deviation_metrics
│   │   └── use_cases/         # RunEpisode, RunExperiment, RunDeviationSuite, RunBaselineComparison
│   ├── infrastructure/
│   │   ├── datasets/          # HFFEVERRepository
│   │   ├── verifiers/         # FEVERGroundTruthVerifier, LLMEvidenceEvaluator, verifier_factory
│   │   ├── storage/           # JSONLStorage, ReputationStore
│   │   ├── llm/               # OpenAIClient
│   │   └── frameworks/        # AutoGenAdapter
│   └── interfaces/
│       ├── cli/               # main.py (Milestone 1)
│       └── configs/          # milestone1.yaml, ...
├── scripts/
│   ├── debug_evidence_verifier.py
│   └── aggregate_multi_seed_results.py
├── results/                    # Outputs (JSON, JSONL)
├── .env.example
├── SUBMISSION_RUN.md           # Chi tiết chạy submission
├── SETUP.md                    # Milestone 1 setup
├── QUICK_START.md              # Quick start experiments
└── README.md
```

---

## Troubleshooting

### ModuleNotFoundError / Import errors

- Run from the project root: `cd /path/to/MAScheaptalk` then `python run_all_milestones.py`.
- Ensure the virtual environment is activated: `source .venv/bin/activate`.
- Reinstall dependencies: `pip install -r requirements.txt`.
- Run `python validate_setup.py` to check all imports.

### OpenAI API key not set

- Create `.env` from `.env.example` and set `OPENAI_API_KEY=sk-your-key`.
- Or export: `export OPENAI_API_KEY=sk-your-key`.

### FEVER dataset fails to load

- The code falls back to mock data if HuggingFace FEVER cannot be loaded; the pipeline still runs.
- To clear cache and retry: `rm -rf ~/.cache/huggingface/datasets/fever` then run again.
- Ensure network access to HuggingFace; `datasets` is in `requirements.txt`.

### evidence_match_score always 0

- Ensure the dataset provides real evidence text (not placeholders); see `HFFEVERRepository` and `FEVERGroundTruthVerifier` for extraction logic.
- Optionally enable `USE_LLM_EVIDENCE_EVAL=1` to add LLM-based evidence scoring.

### Long run times / API costs

- Use `NUM_TASKS=10` and `NUM_SAMPLES=10` for quick tests.
- Use `OPENAI_MODEL=gpt-4o-mini` (default) for lower cost; switch to `gpt-4o` only if needed.
- Milestone 4 (P1/P2/P3 × deviations) has the most episodes; expect several hours for 500 tasks with real API.

### Multi-seed: SEEDS not applied

- Set `SEEDS=42,123,456` (comma-separated, no spaces, at least two seeds). If only one value is given, the script runs a single seed.

---

## Development

### Tests

```bash
pytest tests/
```

### Adding a new protocol

1. Add a class in `src/application/protocols/` inheriting from `BaseProtocol`.
2. Implement `get_sender_system_prompt`, `get_receiver_system_prompt`, `get_protocol_id`, `get_config`.
3. Wire it in the relevant runner (e.g. `run_milestone4_protocols.py`) and config if needed.

### Adding a new dataset

1. Implement a repository in `src/infrastructure/datasets/` satisfying `DatasetRepository`.
2. Implement a verifier in `src/infrastructure/verifiers/` if the evaluation differs from FEVER.

---

## Roadmap

- [x] Milestone 1: FEVER + P1 Evidence-First + honest/no_evidence
- [x] Milestone 2: All deviations + IRI
- [x] Milestone 3: Baseline comparison (Self-Consistency, Self-Refine)
- [x] Milestone 4: P2 Cross-Examination, P3 Slashing
- [x] Evidence evaluation: string match + optional LLM scoring
- [x] Submission run: NUM_TASKS/NUM_SAMPLES/SEED/SEEDS via .env, multi-seed aggregation
- [ ] Larger-scale runs (e.g. full FEVER dev), additional benchmarks

---

## Citation

```bibtex
@article{mas-cheaptalk-2026,
  title={Truthful Communication in LLM Multi-Agent Systems: Protocol Design with Cheap Talk},
  author={...},
  year={2026}
}
```

---

## License

See [LICENSE](LICENSE).
