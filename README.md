# MAS Cheap Talk: Communication Protocols for LLM Multi-Agent Systems

Implementation of Milestone 1: Evidence-First protocol (P1) with FEVER dataset.

## Overview

This project implements a game-theoretic approach to communication protocols in LLM-based multi-agent systems (MAS). The goal is to design protocols that make truthful communication incentive-compatible and reduce the benefits of lying or withholding evidence.

### Milestone 1: "Hello Research Loop"

- **Dataset**: FEVER (Fact Extraction and VERification)
- **Protocol**: P1 Evidence-First (Claim → Evidence → Decision)
- **Agents**: Sender (claims with evidence) + Receiver (evaluates evidence)
- **Verifier**: Ground truth checker for label and evidence correctness
- **Deviation Test**: "no_evidence" - tests if protocol penalizes missing evidence

## Architecture

Clean Architecture with 4 layers:

```
src/
├── domain/          # Entities, value objects, ports (interfaces)
├── application/     # Use cases, protocols, scoring
├── infrastructure/  # LLM clients, datasets, verifiers, storage
└── interfaces/      # CLI, configs
```

## Installation

### Prerequisites

- Python 3.11.14
- pip

### Setup

1. Create virtual environment:

```bash
python3.11 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Configure environment:

```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

## Usage

### Run Milestone 1 Experiment

```bash
python src/interfaces/cli/main.py --config src/interfaces/configs/milestone1.yaml
```

This will:
- Load 100 tasks from FEVER validation set
- Run each task with "honest" and "no_evidence" deviation strategies
- Save episodes to `results/milestone1.jsonl`
- Compute and display metrics including Deviation Gain (DG)

### Configuration

Edit `src/interfaces/configs/milestone1.yaml` to customize:

- `num_tasks`: Number of FEVER tasks to process
- `llm.model`: Model to use (e.g., "gpt-4o", "gpt-4")
- `deviations`: List of deviation strategies to test
- `payoff.lambda_cost`: Cost weight in payoff function
- `payoff.mu_penalty`: Penalty weight for protocol violations

### Override Config via CLI

```bash
# Run with fewer tasks for quick testing
python src/interfaces/cli/main.py --num-tasks 10

# Change output location
python src/interfaces/cli/main.py --output results/test_run.jsonl
```

## Key Concepts

### Protocol P1: Evidence-First

Enforces schema: **Claim → Evidence → Decision**

- **Sender** must provide evidence with claims
- **Receiver** evaluates evidence quality before accepting
- Missing or weak evidence results in penalty

### Deviation Gain (DG)

Measures whether deviating from honest behavior is advantageous:

```
DG = mean(payoff_deviation) - mean(payoff_honest)
```

- **DG < 0**: Protocol is effective (deviation is disadvantageous) ✓
- **DG > 0**: Protocol needs improvement (deviation is advantageous) ✗

### Payoff Function

```
Payoff = quality - λ * cost - μ * penalty
```

Where:
- **quality**: Weighted accuracy + evidence match + compliance
- **cost**: Token usage cost
- **penalty**: Penalty for protocol violations (e.g., missing evidence)

## Metrics

### Task-level

- **Accuracy**: % episodes with correct label
- **Evidence compliance**: % episodes with evidence provided
- **Evidence match**: Average similarity to ground truth evidence (0-1)

### Game-theoretic

- **Deviation Gain**: Mean payoff difference between deviation and honest
- **% DG > 0**: Percentage of cases where deviation was advantageous

### Cost

- **Total tokens**: Token usage across all episodes
- **Mean cost**: Average cost per episode

## Expected Results

For Milestone 1, we expect:

- **Honest episodes**: High accuracy, high evidence compliance
- **No_evidence episodes**: Lower accuracy, zero evidence compliance, negative payoff
- **DG (no_evidence)**: Negative value, indicating protocol effectiveness

## Project Structure

```
MAScheaptalk/
├── src/
│   ├── domain/
│   │   ├── entities/      # Task, Episode, Message, Evidence
│   │   ├── value_objects/ # AgentRole, FEVERLabel
│   │   └── ports/         # Interfaces (LLMClient, Verifier, etc.)
│   ├── application/
│   │   ├── protocols/     # P1 Evidence-First
│   │   ├── use_cases/     # RunEpisode, RunExperiment
│   │   └── scoring/       # FEVERScoring
│   ├── infrastructure/
│   │   ├── datasets/      # HFFEVERRepository
│   │   ├── verifiers/     # FEVERGroundTruthVerifier
│   │   ├── storage/       # JSONLStorage
│   │   ├── llm/           # OpenAIClient, LocalClient
│   │   └── frameworks/    # AutoGenAdapter
│   └── interfaces/
│       ├── cli/           # main.py
│       └── configs/       # milestone1.yaml
├── results/               # Experiment outputs (JSONL + summaries)
├── tests/                 # Unit and integration tests
├── requirements.txt
├── .env.example
└── README.md
```

## Development

### Running Tests

```bash
pytest tests/
```

### Adding New Protocols

1. Create new protocol class in `src/application/protocols/`
2. Inherit from `BaseProtocol`
3. Implement system prompts for Sender and Receiver
4. Update config and CLI to support new protocol

### Adding New Datasets

1. Create new repository class in `src/infrastructure/datasets/`
2. Inherit from `DatasetRepository`
3. Implement `get_task()` and `iter_tasks()`
4. Create corresponding verifier in `src/infrastructure/verifiers/`

## Roadmap

- [x] Milestone 1: FEVER + P1 Evidence-First + honest/no_evidence
- [ ] Milestone 2: Additional deviations (lie, withhold) + payoff analysis
- [ ] Milestone 3: Baseline comparisons (Self-Consistency, Self-Refine, Debate)
- [ ] Milestone 4: P2 Cross-Examination protocol
- [ ] Milestone 5: P3 Reputation/Slashing mechanism
- [ ] Milestone 6: HotpotQA multi-hop reasoning
- [ ] Milestone 7: Full paper results and analysis

## Citation

```
@article{mas-cheaptalk-2026,
  title={Truthful Communication in LLM Multi-Agent Systems: Protocol Design with Cheap Talk},
  author={...},
  year={2026}
}
```

## License

See LICENSE file.
