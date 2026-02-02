# Setup Guide for Milestone 1

## Quick Start

Follow these steps to set up and run the Milestone 1 experiment:

### 1. Install Dependencies

```bash
# Create virtual environment (recommended)
python3.11 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install required packages
pip install -r requirements.txt
```

### 2. Configure API Key

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your OpenAI API key
# OPENAI_API_KEY=sk-your-actual-api-key-here
```

### 3. Validate Setup

Run the validation script to ensure everything is working:

```bash
python validate_setup.py
```

This will:
- Test all imports
- Load a small sample from FEVER dataset
- Initialize the P1 protocol

### 4. Run Experiment

#### Option A: Full Experiment (100 tasks, ~$5-10 cost)

```bash
python src/interfaces/cli/main.py
```

#### Option B: Quick Test (10 tasks, ~$0.50-1 cost)

```bash
python src/interfaces/cli/main.py --num-tasks 10
```

#### Option C: Minimal Test (2 tasks, for debugging)

```bash
python src/interfaces/cli/main.py --num-tasks 2
```

### 5. View Results

Results are saved to:
- `results/milestone1.jsonl` - Detailed episode data (one episode per line)
- `results/milestone1_summary.json` - Aggregate metrics and Deviation Gain

View summary:

```bash
cat results/milestone1_summary.json | python -m json.tool
```

## Expected Output

### During Execution

```
Loading FEVER dataset: split=validation, num_samples=100
Loaded 100 tasks from FEVER

Starting experiment with 100 tasks
Deviation types: ['honest', 'no_evidence']

Processing task 1/100: fever_12345
  Running with deviation_type=honest
    Label correct: True
    Evidence provided: True
    Payoff: 0.843
  Running with deviation_type=no_evidence
    Label correct: False
    Evidence provided: False
    Payoff: -0.234
...
```

### Final Results

```
EXPERIMENT RESULTS
============================================================

HONEST:
  Accuracy: 0.820
  Evidence compliance: 0.950
  Evidence match: 0.650
  Mean payoff: 0.756
  Mean cost: 0.000125

NO_EVIDENCE:
  Accuracy: 0.450
  Evidence compliance: 0.000
  Evidence match: 0.000
  Mean payoff: -0.123
  Mean cost: 0.000089

DEVIATION GAIN ANALYSIS:

  no_evidence vs honest:
    Deviation Gain: -0.879
    % episodes with DG > 0: 8.0%
    ✓ Protocol is effective! Deviation is disadvantageous.
============================================================
```

## Troubleshooting

### ImportError: No module named 'autogen_agentchat'

```bash
pip install autogen-agentchat[llm]~=0.2 autogen-ext[openai]~=0.2
```

### ImportError: No module named 'datasets'

```bash
pip install datasets>=2.13.0
```

### OpenAI API Key Error

Make sure `.env` file exists and contains:
```
OPENAI_API_KEY=sk-your-actual-key
```

Or export it:
```bash
export OPENAI_API_KEY=sk-your-actual-key
```

### FEVER Dataset Loading Errors

If FEVER dataset fails to load, it will try alternative configurations automatically. 
If issues persist, you can:

1. Clear HuggingFace cache:
```bash
rm -rf ~/.cache/huggingface/datasets/fever
```

2. Try downloading manually:
```python
from datasets import load_dataset
ds = load_dataset("fever", "v1.0", split="validation[:10]", trust_remote_code=True)
```

## Configuration Options

Edit `src/interfaces/configs/milestone1.yaml` to customize:

```yaml
experiment:
  num_tasks: 100        # Number of FEVER tasks
  seed: 42              # Random seed

llm:
  provider: "openai"    # or "local"
  model: "gpt-4o"       # or "gpt-4", "gpt-3.5-turbo"

deviations:
  - "honest"            # Baseline
  - "no_evidence"       # Test protocol

payoff:
  lambda_cost: 0.01     # Cost weight (lower = less penalty for token usage)
  mu_penalty: 0.5       # Protocol violation penalty
```

## Cost Estimates

Based on GPT-4o pricing (~$0.01/1K tokens):

- **2 tasks**: ~$0.10
- **10 tasks**: ~$0.50-1.00
- **100 tasks**: ~$5-10 (depending on conversation length)

Each task runs 2 episodes (honest + no_evidence), and each episode involves:
- 1 Sender message (~200-500 tokens)
- 1 Receiver message (~100-300 tokens)

## Next Steps

After Milestone 1 is complete:

1. **Analyze Results**: Review the metrics in `results/milestone1_summary.json`
2. **Inspect Episodes**: Use `results/milestone1.jsonl` to see individual conversations
3. **Adjust Parameters**: Try different `lambda_cost` and `mu_penalty` values
4. **Add Deviations**: Implement "lie" and "withhold" strategies
5. **Compare Baselines**: Implement Self-Consistency, Self-Refine, Debate

See README.md for full project roadmap.
