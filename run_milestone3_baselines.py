"""Run Milestone 3: Baseline Comparison experiments."""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from infrastructure.datasets.hf_fever_repo import HFFEVERRepository
from infrastructure.verifiers.verifier_factory import create_fever_verifier
from infrastructure.storage.jsonl_storage import JSONLStorage
from infrastructure.llm.openai_client import OpenAIClient
from infrastructure.llm.api_key_pool import APIKeyPool
from domain.entities.payoff import PayoffConfig
from application.protocols.p1_evidence_first import P1EvidenceFirstProtocol
from application.baselines.self_consistency import SelfConsistency
from application.baselines.self_refine import SelfRefine
from application.use_cases.run_episode import RunEpisode
from application.use_cases.run_baseline_comparison import RunBaselineComparison


def _get_submission_config():
    """Read task/sample/seed from env for submission runs. Default: 500 tasks, seed 42."""
    def _int_env(name: str, default: int) -> int:
        v = os.getenv(name)
        if v is None or v.strip() == "":
            return default
        try:
            return max(1, int(v.strip()))
        except ValueError:
            return default
    return (_int_env("NUM_TASKS", 500), _int_env("NUM_SAMPLES", 500), 
            _int_env("SEED", 42), _int_env("MAX_CONCURRENT_EPISODES", 30))


def main():
    """Run Milestone 3: Baseline Comparison."""
    
    # Load environment
    load_dotenv()
    
    num_tasks, num_samples, seed, max_concurrent = _get_submission_config()
    
    print("="*80)
    print("MILESTONE 3: BASELINE COMPARISON (PARALLEL)")
    print("="*80)
    print("\nThis will compare P1 protocol against strong baselines:")
    print("  1. Self-Consistency (K=5 samples, voting)")
    print("  2. Self-Refine (2 rounds of critique-revise)")
    print("\nConfiguration:")
    print(f"  - Tasks: {num_tasks} (set NUM_TASKS in .env for submission)")
    print(f"  - Samples: {num_samples} (set NUM_SAMPLES in .env)")
    print(f"  - Seed: {seed} (set SEED in .env)")
    print(f"  - Max concurrent: {max_concurrent} (set MAX_CONCURRENT_EPISODES in .env)")
    print("  - Model: gpt-4o-mini (cost-effective)")
    print("  - Budget: 2000 tokens, 10 calls per task")
    print("  - Fair comparison: same LLM, same budget")
    print("="*80)
    
    # Get API keys (support multiple keys)
    api_keys_str = os.getenv('OPENAI_API_KEYS', os.getenv('OPENAI_API_KEY', ''))
    if not api_keys_str:
        print("\n❌ ERROR: OPENAI_API_KEY or OPENAI_API_KEYS not set!")
        print("Please set it:")
        print("  export OPENAI_API_KEY=your-key")
        print("  or for multiple keys: export OPENAI_API_KEYS=key1,key2,key3")
        return 1
    
    # Create API key pool
    api_key_pool = APIKeyPool.from_env_string(
        api_keys_str,
        rate_limit_rpm=int(os.getenv('RATE_LIMIT_RPM', '500'))
    )
    print(f"\n✓ Using {len(api_key_pool)} API key(s) for load balancing")
    
    # For backwards compatibility
    api_key = api_keys_str.split(',')[0].strip()
    
    # Initialize components
    print("\n[1/5] Initializing dataset...")
    dataset_repo = HFFEVERRepository(
        split="dev",  # FEVER uses 'dev' not 'validation'
        num_samples=num_samples,
        seed=seed
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
    
    print("[5/5] Initializing protocol and verifier (evidence: string match + optional LLM eval)...")
    protocol = P1EvidenceFirstProtocol()
    verifier = create_fever_verifier(
        use_semantic_matching=False,
        use_llm_evidence_eval=None,
        llm_model="gpt-4o-mini",
        api_key=api_key,
    )
    
    run_episode = RunEpisode(
        protocol=protocol,
        verifier=verifier,
        model_name="gpt-4o-mini",
        api_key=api_key,
        api_key_pool=api_key_pool,
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
        num_tasks=num_tasks,
        max_tokens_per_task=2000,
        max_calls_per_task=10,
        payoff_config=payoff_config,
        max_concurrent=max_concurrent
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
        
        # Print API key pool stats
        if len(api_key_pool) > 1:
            api_key_pool.print_stats()
        
        # Print key findings
        print("\n📊 KEY FINDINGS:")
        
        methods = results['methods']
        
        # Best accuracy
        best_method = max(methods.items(), key=lambda x: x[1]['accuracy'])
        print(f"\n  Best Accuracy: {best_method[0]}")
        print(f"    - {best_method[1]['accuracy']:.1%}")
        
        # Evidence: compliance and match score
        if 'protocol_p1' in methods:
            p1 = methods['protocol_p1']
            p1_evidence = p1['evidence_compliance']
            p1_match = p1.get('evidence_match_score', 0)
            print(f"\n  Protocol P1 Evidence:")
            print(f"    - Compliance: {p1_evidence:.1%}")
            print(f"    - Match score (vs GT / LLM): {p1_match:.3f}")
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
