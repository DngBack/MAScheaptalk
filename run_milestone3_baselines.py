"""Run Milestone 3: Baseline Comparison experiments."""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from infrastructure.datasets.hf_fever_repo import HFFEVERRepository
from infrastructure.verifiers.fever_groundtruth_verifier import FEVERGroundTruthVerifier
from infrastructure.storage.jsonl_storage import JSONLStorage
from infrastructure.llm.openai_client import OpenAIClient
from domain.entities.payoff import PayoffConfig
from application.protocols.p1_evidence_first import P1EvidenceFirstProtocol
from application.baselines.self_consistency import SelfConsistency
from application.baselines.self_refine import SelfRefine
from application.use_cases.run_episode import RunEpisode
from application.use_cases.run_baseline_comparison import RunBaselineComparison


def main():
    """Run Milestone 3: Baseline Comparison."""
    
    # Load environment
    load_dotenv()
    
    print("="*80)
    print("MILESTONE 3: BASELINE COMPARISON")
    print("="*80)
    print("\nThis will compare P1 protocol against strong baselines:")
    print("  1. Self-Consistency (K=5 samples, voting)")
    print("  2. Self-Refine (2 rounds of critique-revise)")
    print("\nConfiguration:")
    print("  - Tasks: 10 (test run)")
    print("  - Model: gpt-4o-mini (cost-effective)")
    print("  - Budget: 2000 tokens, 10 calls per task")
    print("  - Fair comparison: same LLM, same budget")
    print("="*80)
    
    # Get API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("\n❌ ERROR: OPENAI_API_KEY not set!")
        print("Please set it:")
        print("  export OPENAI_API_KEY=your-key")
        print("  or add to .env file")
        return 1
    
    # Initialize components
    print("\n[1/5] Initializing dataset...")
    dataset_repo = HFFEVERRepository(
        split="dev",  # FEVER uses 'dev' not 'validation'
        num_samples=10,
        seed=42
    )
    
    print("[2/5] Initializing LLM client...")
    llm_client = OpenAIClient(model="gpt-4o-mini", api_key=api_key)
    
    print("[3/5] Initializing storage...")
    storage = JSONLStorage(filepath="results/milestone3/episodes.jsonl")
    
    print("[4/5] Initializing baselines...")
    
    # Baselines
    self_consistency = SelfConsistency(
        llm_client=llm_client,
        k_samples=5,
        temperature=0.7
    )
    
    self_refine = SelfRefine(
        llm_client=llm_client,
        num_rounds=2,
        temperature=0.3
    )
    
    baselines = [self_consistency, self_refine]
    
    print("[5/5] Initializing protocol (for comparison)...")
    protocol = P1EvidenceFirstProtocol()
    verifier = FEVERGroundTruthVerifier(use_semantic_matching=False)
    
    run_episode = RunEpisode(
        protocol=protocol,
        verifier=verifier,
        model_name="gpt-4o-mini",
        api_key=api_key,
        lambda_cost=0.01,
        mu_penalty=0.5
    )
    
    # Payoff config
    payoff_config = PayoffConfig(lambda_cost=0.01, mu_penalty=0.5)
    
    # Baseline comparison
    comparison = RunBaselineComparison(
        dataset_repo=dataset_repo,
        storage=storage,
        llm_client=llm_client,
        num_tasks=10,
        max_tokens_per_task=2000,
        max_calls_per_task=10,
        payoff_config=payoff_config
    )
    
    print("\n" + "="*80)
    print("RUNNING BASELINE COMPARISON")
    print("="*80)
    
    try:
        # Execute
        results = comparison.execute_sync(baselines, run_episode)
        
        # Save results
        output_path = "results/milestone3/baseline_comparison.json"
        comparison.save_results(results, output_path)
        
        print("\n" + "="*80)
        print("✅ MILESTONE 3 COMPLETE")
        print("="*80)
        print(f"\nResults saved to:")
        print(f"  - Episodes: results/milestone3/episodes.jsonl")
        print(f"  - Summary: {output_path}")
        
        # Print key findings
        print("\n📊 KEY FINDINGS:")
        
        methods = results['methods']
        
        # Best accuracy
        best_method = max(methods.items(), key=lambda x: x[1]['accuracy'])
        print(f"\n  Best Accuracy: {best_method[0]}")
        print(f"    - {best_method[1]['accuracy']:.1%}")
        
        # Evidence compliance
        if 'protocol_p1' in methods:
            p1_evidence = methods['protocol_p1']['evidence_compliance']
            print(f"\n  Protocol P1 Evidence Compliance: {p1_evidence:.1%}")
            
            if p1_evidence > 0.9:
                print(f"    ✓✓ UNIQUE VALUE: Only method with high evidence!")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
