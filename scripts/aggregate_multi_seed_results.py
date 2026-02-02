#!/usr/bin/env python3
"""
Aggregate results from multiple seeds into mean ± std for paper tables.

Usage:
  1. Run milestones with different seeds and copy results:
       SEED=42   python run_all_milestones.py  -> then copy JSONs to results/milestone2/seed42.json etc.
       SEED=123  python run_all_milestones.py  -> copy to results/milestone2/seed123.json etc.
       SEED=456  python run_all_milestones.py  -> copy to results/milestone2/seed456.json etc.
  2. Run this script (edit SEED_PATHS below or pass as args):
       python scripts/aggregate_multi_seed_results.py

Output: results/submission_multi_seed_summary.json with mean and std for key metrics.
"""
import json
import os
import sys
from pathlib import Path
from collections import defaultdict

REPO_ROOT = Path(__file__).resolve().parent.parent


def load_json(path: Path) -> dict:
    with open(path, "r") as f:
        return json.load(f)


def mean_std(values: list) -> tuple:
    if not values:
        return None, None
    n = len(values)
    mean = sum(values) / n
    variance = sum((x - mean) ** 2 for x in values) / n if n > 1 else 0
    std = variance ** 0.5
    return mean, std


def aggregate_milestone2(seed_results: list[dict]) -> dict:
    """Aggregate deviation_suite_results from multiple seeds."""
    out = {"seeds": len(seed_results), "mean": {}, "std": {}}
    # IRI
    iris = [r["iri"] for r in seed_results if "iri" in r]
    if iris:
        m, s = mean_std(iris)
        out["mean"]["iri"] = m
        out["std"]["iri"] = s
    # metrics_by_type: for each deviation_type, aggregate accuracy, evidence_compliance, evidence_match_score, mean_payoff
    by_type = defaultdict(list)
    for r in seed_results:
        for dev_type, metrics in r.get("metrics_by_type", {}).items():
            by_type[dev_type].append(metrics)
    out["metrics_by_type"] = {}
    for dev_type, list_of_metrics in by_type.items():
        out["metrics_by_type"][dev_type] = {}
        for key in ["accuracy", "evidence_compliance", "evidence_match_score", "mean_payoff"]:
            vals = [m[key] for m in list_of_metrics if key in m]
            if vals:
                m, s = mean_std(vals)
                out["metrics_by_type"][dev_type][f"{key}_mean"] = m
                out["metrics_by_type"][dev_type][f"{key}_std"] = s
    # deviation_gains: for each deviation type, aggregate deviation_gain, percent_dg_positive
    dg_by_type = defaultdict(list)
    for r in seed_results:
        for dev_type, dg in r.get("deviation_gains", {}).items():
            dg_by_type[dev_type].append(dg)
    out["deviation_gains"] = {}
    for dev_type, list_dg in dg_by_type.items():
        dg_vals = [d["deviation_gain"] for d in list_dg if "deviation_gain" in d]
        pct_vals = [d["percent_dg_positive"] for d in list_dg if "percent_dg_positive" in d]
        out["deviation_gains"][dev_type] = {}
        if dg_vals:
            m, s = mean_std(dg_vals)
            out["deviation_gains"][dev_type]["deviation_gain_mean"] = m
            out["deviation_gains"][dev_type]["deviation_gain_std"] = s
        if pct_vals:
            m, s = mean_std(pct_vals)
            out["deviation_gains"][dev_type]["percent_dg_positive_mean"] = m
            out["deviation_gains"][dev_type]["percent_dg_positive_std"] = s
    return out


def aggregate_milestone3(seed_results: list[dict]) -> dict:
    """Aggregate baseline_comparison from multiple seeds."""
    out = {"seeds": len(seed_results), "methods": {}}
    method_names = set()
    for r in seed_results:
        method_names.update(r.get("methods", {}).keys())
    for method in method_names:
        list_metrics = []
        for r in seed_results:
            if method in r.get("methods", {}):
                list_metrics.append(r["methods"][method])
        if not list_metrics:
            continue
        out["methods"][method] = {}
        for key in ["accuracy", "evidence_compliance", "evidence_match_score", "mean_payoff"]:
            vals = [m[key] for m in list_metrics if key in m]
            if vals:
                m, s = mean_std(vals)
                out["methods"][method][f"{key}_mean"] = m
                out["methods"][method][f"{key}_std"] = s
    return out


def aggregate_milestone4(seed_results: list[dict]) -> dict:
    """Aggregate protocol_comparison (per-protocol) from multiple seeds."""
    out = {"seeds": len(seed_results), "protocols": {}}
    # Each seed_result is { "P1_Evidence_First": {...}, "P2_Cross_Exam": {...}, "P3_Slashing": {...} }
    protocol_names = set()
    for r in seed_results:
        protocol_names.update(r.keys())
    for proto in protocol_names:
        list_results = [r[proto] for r in seed_results if proto in r]
        if not list_results:
            continue
        out["protocols"][proto] = {
            "iri_mean": mean_std([x.get("iri", 0) for x in list_results])[0],
            "iri_std": mean_std([x.get("iri", 0) for x in list_results])[1],
        }
        # honest metrics
        honest_list = [x.get("metrics_by_type", {}).get("honest", {}) for x in list_results]
        honest_list = [h for h in honest_list if h]
        if honest_list:
            for key in ["accuracy", "evidence_compliance", "evidence_match_score", "mean_payoff"]:
                vals = [h[key] for h in honest_list if key in h]
                if vals:
                    m, s = mean_std(vals)
                    out["protocols"][proto][f"honest_{key}_mean"] = m
                    out["protocols"][proto][f"honest_{key}_std"] = s
    return out


def main():
    # Default: look for seed-specific files in results/
    # User can copy deviation_suite_results.json -> results/milestone2/seed42.json etc.
    seeds = [42, 123, 456]
    if os.getenv("SEEDS"):
        seeds = [int(x) for x in os.getenv("SEEDS").strip().split(",")]

    results_dir = REPO_ROOT / "results"
    summary = {"seeds": seeds, "milestone2": None, "milestone3": None, "milestone4": None}

    # Milestone 2
    m2_dir = results_dir / "milestone2"
    m2_files = [m2_dir / f"seed{s}.json" for s in seeds]
    if all(p.exists() for p in m2_files):
        seed_results = [load_json(p) for p in m2_files]
        summary["milestone2"] = aggregate_milestone2(seed_results)
        print("Milestone 2: aggregated from", [str(p) for p in m2_files])
    else:
        print("Milestone 2: missing seed files (expected e.g. results/milestone2/seed42.json). Skip.")

    # Milestone 3
    m3_dir = results_dir / "milestone3"
    m3_files = [m3_dir / f"seed{s}.json" for s in seeds]
    if all(p.exists() for p in m3_files):
        seed_results = [load_json(p) for p in m3_files]
        summary["milestone3"] = aggregate_milestone3(seed_results)
        print("Milestone 3: aggregated from", [str(p) for p in m3_files])
    else:
        print("Milestone 3: missing seed files. Skip.")

    # Milestone 4: each seed is one protocol_comparison.json; we need one file per seed
    m4_dir = results_dir / "milestone4"
    m4_files = [m4_dir / f"protocol_comparison_seed{s}.json" for s in seeds]
    if all(p.exists() for p in m4_files):
        seed_results = [load_json(p) for p in m4_files]
        summary["milestone4"] = aggregate_milestone4(seed_results)
        print("Milestone 4: aggregated from", [str(p) for p in m4_files])
    else:
        print("Milestone 4: missing protocol_comparison_seed*.json. Skip.")

    out_path = results_dir / "submission_multi_seed_summary.json"
    results_dir.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(summary, f, indent=2)
    print("\nSummary written to:", out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
