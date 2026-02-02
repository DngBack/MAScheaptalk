"""Run all milestones sequentially to get complete results.

Evidence evaluation (used in all milestones):
  - String/semantic match: provided evidence vs ground-truth sentences (overlap / similarity).
  - Optional LLM evaluation: set USE_LLM_EVIDENCE_EVAL=1 to also score each evidence sentence
    via LLM (relevance, support for claim), then aggregate; combined with string match (default 0.5/0.5).
  - Results show evidence_match_score (and evidence_compliance) in summaries and JSON outputs.

Multi-seed (paper submission): set SEEDS=42,123,456 in .env to run all seeds in one go.
  Each seed runs M2 → M3 → M4; results are copied to seed{seed}.json; then mean±std is aggregated.
"""
import os
import sys
import subprocess
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent


def _parse_seeds(env_seeds: str) -> list[int] | None:
    """Parse SEEDS env (e.g. '42,123,456') into list of int. Return None if empty/single."""
    s = (env_seeds or "").strip()
    if not s:
        return None
    parts = [p.strip() for p in s.split(",") if p.strip()]
    if len(parts) <= 1:
        return None
    try:
        return [int(p) for p in parts]
    except ValueError:
        return None


def run_script(script_name: str, description: str, env: dict | None = None) -> bool:
    """Run a Python script and return success status."""
    print("\n" + "="*80)
    print(f"RUNNING: {description}")
    print("="*80)
    
    run_env = {**os.environ, **(env or {})}
    try:
        subprocess.run(
            [sys.executable, script_name],
            check=True,
            capture_output=False,
            env=run_env,
            cwd=REPO_ROOT,
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Failed to run {script_name}")
        return False


def run_one_seed(seed: int, copy_to_seed_files: bool) -> list[tuple[str, bool]]:
    """Run M2, M3, M4 with SEED=seed. If copy_to_seed_files, copy results to seed{seed}.json."""
    env = {**os.environ, "SEED": str(seed)}
    results = []
    
    success = run_script("run_milestone2_deviation.py", f"Milestone 2 (SEED={seed})", env=env)
    results.append(("Milestone 2", success))
    if success and copy_to_seed_files:
        src = REPO_ROOT / "results" / "milestone2" / "deviation_suite_results.json"
        dst = REPO_ROOT / "results" / "milestone2" / f"seed{seed}.json"
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            print(f"  → Copied to {dst.name}")
    
    success = run_script("run_milestone3_baselines.py", f"Milestone 3 (SEED={seed})", env=env)
    results.append(("Milestone 3", success))
    if success and copy_to_seed_files:
        src = REPO_ROOT / "results" / "milestone3" / "baseline_comparison.json"
        dst = REPO_ROOT / "results" / "milestone3" / f"seed{seed}.json"
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            print(f"  → Copied to {dst.name}")
    
    success = run_script("run_milestone4_protocols.py", f"Milestone 4 (SEED={seed})", env=env)
    results.append(("Milestone 4", success))
    if success and copy_to_seed_files:
        src = REPO_ROOT / "results" / "milestone4" / "protocol_comparison.json"
        dst = REPO_ROOT / "results" / "milestone4" / f"protocol_comparison_seed{seed}.json"
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            print(f"  → Copied to {dst.name}")
    
    return results


def run_aggregate(seeds: list[int]) -> bool:
    """Run aggregate script to produce submission_multi_seed_summary.json."""
    agg_script = REPO_ROOT / "scripts" / "aggregate_multi_seed_results.py"
    if not agg_script.exists():
        print("  (aggregate script not found, skip)")
        return False
    env = {**os.environ, "SEEDS": ",".join(str(s) for s in seeds)}
    try:
        subprocess.run(
            [sys.executable, str(agg_script)],
            check=True,
            env=env,
            cwd=REPO_ROOT,
        )
        return True
    except subprocess.CalledProcessError:
        return False


def main():
    """Run all milestones. If SEEDS is set (e.g. 42,123,456), run each seed and aggregate."""
    from dotenv import load_dotenv
    load_dotenv(REPO_ROOT / ".env")
    
    use_llm_evidence = os.getenv("USE_LLM_EVIDENCE_EVAL", "").strip().lower() in ("1", "true", "yes")
    num_tasks = os.getenv("NUM_TASKS", "").strip() or "500"
    num_samples = os.getenv("NUM_SAMPLES", "").strip() or "500"
    seed = os.getenv("SEED", "").strip() or "42"
    seeds_list = _parse_seeds(os.getenv("SEEDS", ""))
    
    multi_seed = seeds_list is not None and len(seeds_list) >= 2
    
    print("="*80)
    print("COMPLETE MILESTONE EXECUTION")
    print("="*80)
    print("\nThis will run all three milestones:")
    print("  1. Milestone 2: Deviation Suite")
    print("  2. Milestone 3: Baseline Comparison")
    print("  3. Milestone 4: Protocol Progression (P1→P2→P3)")
    print(f"\nScale: NUM_TASKS={num_tasks}, NUM_SAMPLES={num_samples}")
    if multi_seed:
        print(f"Mode: MULTI-SEED (SEEDS={','.join(map(str, seeds_list))}) — run each seed then aggregate mean±std")
    else:
        print(f"Mode: single run SEED={seed} (set SEEDS=42,123,456 in .env for multi-seed in one go)")
    print("\nEvidence evaluation: string match vs ground truth", end="")
    if use_llm_evidence:
        print(" + LLM per-sentence scoring (USE_LLM_EVIDENCE_EVAL=1)")
    else:
        print(" (set USE_LLM_EVIDENCE_EVAL=1 for LLM evidence scoring)")
    print("\nEstimated time: depends on NUM_TASKS and number of seeds")
    print("="*80)
    
    input("\nPress Enter to continue or Ctrl+C to cancel...")
    
    if multi_seed:
        all_results = []
        for i, s in enumerate(seeds_list):
            print("\n" + "#"*80)
            print(f"# SEED {i+1}/{len(seeds_list)}: {s}")
            print("#"*80)
            all_results.extend(run_one_seed(s, copy_to_seed_files=True))
        
        print("\n" + "="*80)
        print("AGGREGATING MULTI-SEED RESULTS (mean ± std)")
        print("="*80)
        if run_aggregate(seeds_list):
            print("  → results/submission_multi_seed_summary.json")
        print("\n" + "="*80)
        print("EXECUTION SUMMARY (multi-seed)")
        print("="*80)
        for name, success in all_results:
            status = "✅ SUCCESS" if success else "❌ FAILED"
            print(f"  {name:<20} {status}")
        print("\n📊 KEY FILE: results/submission_multi_seed_summary.json (for paper tables)")
        all_success = all(s for _, s in all_results)
        return 0 if all_success else 1
    
    # Single run
    results = []
    results.append(("Milestone 2", run_script("run_milestone2_deviation.py", "Milestone 2: Deviation Suite")))
    if not results[-1][1]:
        print("\n⚠ Milestone 2 failed, continuing anyway...")
    results.append(("Milestone 3", run_script("run_milestone3_baselines.py", "Milestone 3: Baseline Comparison")))
    if not results[-1][1]:
        print("\n⚠ Milestone 3 failed, continuing anyway...")
    results.append(("Milestone 4", run_script("run_milestone4_protocols.py", "Milestone 4: Protocol Progression")))
    
    print("\n" + "="*80)
    print("EXECUTION SUMMARY")
    print("="*80)
    for milestone, success in results:
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"  {milestone:<20} {status}")
    print("\n📁 RESULTS LOCATION:")
    print("  - Milestone 2: results/milestone2/deviation_suite_results.json")
    print("  - Milestone 3: results/milestone3/baseline_comparison.json")
    print("  - Milestone 4: results/milestone4/protocol_comparison.json")
    print("\n📋 EVIDENCE METRICS (in JSON and console):")
    print("  - evidence_match_score, evidence_compliance")
    print("="*80)
    all_success = all(s for _, s in results)
    if all_success:
        print("✅ ALL MILESTONES COMPLETED SUCCESSFULLY!")
        print("  ✓ Deviation Gain (DG), IRI, Baseline comparison, Protocol progression (P1→P2→P3)")
    else:
        print("⚠ Some milestones failed. Check logs above.")
    return 0 if all_success else 1


if __name__ == "__main__":
    sys.exit(main())
