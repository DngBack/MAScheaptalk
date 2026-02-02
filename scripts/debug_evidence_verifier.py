#!/usr/bin/env python3
"""
Debug script for evidence verification.
Run one episode (mock data) and print verifier additional_info so you can see
evidence_validity_skipped_reason, num_gt_sentences, num_provided_sentences, evidence_match_score.
Optional: --llm-eval to enable LLM-based per-sentence evidence scoring.
Usage (from repo root, with venv activated):
  python scripts/debug_evidence_verifier.py
  python scripts/debug_evidence_verifier.py --llm-eval
"""
import argparse
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from dotenv import load_dotenv
load_dotenv(REPO_ROOT / ".env")

from infrastructure.datasets.hf_fever_repo import HFFEVERRepository
from infrastructure.verifiers.fever_groundtruth_verifier import FEVERGroundTruthVerifier
from infrastructure.verifiers.llm_evidence_evaluator import LLMEvidenceEvaluator
from infrastructure.llm.openai_client import OpenAIClient
from application.protocols.p1_evidence_first import P1EvidenceFirstProtocol
from application.use_cases.run_episode import RunEpisode


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--llm-eval", action="store_true", help="Use LLM to score each evidence sentence")
    args = parser.parse_args()

    print("Loading mock dataset (with real evidence text)...")
    repo = HFFEVERRepository(split="validation", num_samples=5)
    task = repo.get_task(0)
    print(f"  Task: {task.task_id}, claim: {task.claim[:60]}...")
    print(f"  Ground truth evidence count: {len(task.evidence)}")
    for i, e in enumerate(task.evidence):
        print(f"    GT[{i}]: {e.text[:80]}...")

    llm_evaluator = None
    evidence_weights = None
    if args.llm_eval:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("Error: OPENAI_API_KEY required for --llm-eval")
            sys.exit(1)
        eval_client = OpenAIClient(model=os.getenv("OPENAI_MODEL", "gpt-4o"), api_key=api_key)
        llm_evaluator = LLMEvidenceEvaluator(llm_client=eval_client, temperature=0.0, max_tokens=800)
        evidence_weights = {"string_match": 0.5, "llm": 0.5}
        print("  LLM evidence evaluator: enabled (scores per sentence, then aggregate)")
    verifier = FEVERGroundTruthVerifier(
        use_semantic_matching=False,
        overlap_threshold=0.3,
        llm_evidence_evaluator=llm_evaluator,
        evidence_score_weights=evidence_weights,
    )
    protocol = P1EvidenceFirstProtocol()
    run_episode = RunEpisode(
        protocol=protocol,
        verifier=verifier,
        model_name=os.getenv("OPENAI_MODEL", "gpt-4o"),
        api_key=os.getenv("OPENAI_API_KEY"),
        lambda_cost=0.01,
        mu_penalty=0.5,
    )

    print("\nRunning one honest episode...")
    episode = run_episode.execute_sync(task, deviation_type="honest")

    print("\n--- Verifier additional_info (evidence debug) ---")
    if episode.verifier_result and episode.verifier_result.additional_info:
        for k, v in episode.verifier_result.additional_info.items():
            print(f"  {k}: {v}")
    print(f"\n  evidence_provided: {episode.verifier_result.evidence_provided}")
    print(f"  evidence_match_score: {episode.verifier_result.evidence_match_score}")
    print("\n--- First Sender message (first 500 chars) ---")
    for m in episode.transcript:
        if str(m.role) == "sender":
            print(m.content[:500])
            print(f"  message.evidence count: {len(m.evidence or [])}")
            break
    print("\nDone.")


if __name__ == "__main__":
    main()
