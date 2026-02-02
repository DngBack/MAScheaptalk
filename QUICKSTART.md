# Quick Start Guide

## Step 1: Install Dependencies

Your virtual environment is already created (`cheaptalk`). Now install the required packages:

```bash
# Make sure you're in the virtual environment (you should see (cheaptalk) in your prompt)
# If not, activate it:
source /path/to/venv/cheaptalk/bin/activate

# Install dependencies
pip install -r requirements.txt
```

This will install:
- `autogen-agentchat` and `autogen-ext` for multi-agent framework
- `datasets` for FEVER dataset
- `openai` for LLM API
- `transformers`, `sentence-transformers` for NLP
- Other supporting packages

**Expected time**: 2-5 minutes

## Step 2: Configure API Key

```bash
# Your .env file already exists, make sure it has your OpenAI API key:
cat .env

# It should contain:
# OPENAI_API_KEY=sk-your-actual-api-key-here

# If not set, edit it:
nano .env  # or use your preferred editor
```

## Step 3: Validate Setup

```bash
python validate_setup.py
```

**Expected output:**
```
============================================================
SETUP VALIDATION
============================================================
Testing imports...
  ✓ Domain entities
  ✓ Domain ports
  ✓ Protocols
  ✓ Use cases
  ✓ Scoring
  ✓ Infrastructure

All imports successful! ✓

Testing FEVER dataset loading...
  Loading 5 samples from FEVER...
  ✓ Loaded task: ...
  
Testing P1 protocol...
  ✓ Protocol ID: p1_evidence_first
  ...

============================================================
SUMMARY
============================================================
Imports             : ✓ PASS
FEVER Dataset       : ✓ PASS
P1 Protocol         : ✓ PASS

✓ All validation checks passed!
```

## Step 4: Run Quick Test (2 tasks, ~$0.20)

```bash
python src/interfaces/cli/main.py --num-tasks 2
```

This will:
- Load 2 FEVER tasks
- Run each with honest + no_evidence strategies (4 episodes total)
- Save results to `results/milestone1.jsonl`
- Display metrics and Deviation Gain

**Expected time**: 1-2 minutes

## Step 5: Run Full Experiment (100 tasks, ~$5-10)

Once the quick test works:

```bash
python src/interfaces/cli/main.py
```

**Expected time**: 20-40 minutes (depends on API speed)

## Troubleshooting

### Error: "No module named 'datasets'"

Solution:
```bash
pip install datasets>=2.13.0
```

### Error: "No module named 'autogen_agentchat'"

Solution:
```bash
pip install autogen-agentchat[llm]~=0.2 autogen-ext[openai]~=0.2
```

### Error: "OPENAI_API_KEY not set"

Solution:
```bash
# Edit .env file
echo "OPENAI_API_KEY=sk-your-key-here" > .env
```

### FEVER Dataset Loading Slow

First time loading FEVER dataset downloads from HuggingFace (~300MB). This is normal and cached for future runs.

## Current Status

Based on your terminal output, you need to:

1. ✅ Virtual environment created (`cheaptalk`)
2. ⏳ **Install dependencies** (`pip install -r requirements.txt`)
3. ✅ `.env` file exists (check if API key is set)
4. ⏳ Run validation
5. ⏳ Run experiment

## Next Command to Run

```bash
pip install -r requirements.txt
```

Then run validation again:

```bash
python validate_setup.py
```

## File Structure Check

If you want to verify all files are in place:

```bash
# Check main components
ls -la src/domain/entities/
ls -la src/application/protocols/
ls -la src/infrastructure/datasets/
ls -la src/interfaces/cli/

# Check config
cat src/interfaces/configs/milestone1.yaml
```

All files should be present from the implementation.
