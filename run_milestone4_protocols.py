"""Run Milestone 4: Protocol Comparison (P1, P2, P3) experiments."""
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
from infrastructure.storage.reputation_store import ReputationStore
from domain.entities.payoff import PayoffConfig
from domain.entities.reputation import ReputationConfig
from application.protocols.p1_evidence_first import P1EvidenceFirstProtocol
from application.protocols.p2_cross_exam import P2CrossExamProtocol
from application.protocols.p3_slashing import P3SlashingProtocol
from application.use_cases.run_episode import RunEpisode
from application.use_cases.run_deviation_suite import RunDeviationSuite


def main():
    """Run Milestone 4: Protocol Comparison."""
    
    # Load environment
    load_dotenv()
    
    print("="*80)
    print("MILESTONE 4: PROTOCOL PROGRESSION (P1 → P2 → P3)")
    print("="*80)
    print("\nThis will compare protocol effectiveness:")
    print("  - P1: Evidence-First")
    print("  - P2: Evidence-First + Cross-Examination")
    print("  - P3: Evidence-First + Cross-Exam + Reputation/Slashing")
    print("\nExpected: P1 < P2 < P3 (increasing robustness)")
    print("\nConfiguration:")
    print("  - Tasks: 10 per protocol (test run)")
    print("  - Model: gpt-4o-mini (cost-effective)")
    print("  - Deviation types: honest, lie, withhold, persuasion_only")
    print("="*80)
    
    # Get API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("\n❌ ERROR: OPENAI_API_KEY not set!")
        print("Please set it:")
        print("  export OPENAI_API_KEY=your-key")
        print("  or add to .env file")
        return 1
    
    # Payoff config
    payoff_config = PayoffConfig(lambda_cost=0.01, mu_penalty=0.5)
    
    # Reputation config (for P3)
    reputation_config = ReputationConfig(
        alpha=0.1,
        floor=0.2,
        threshold=0.5,
        slashing_penalty=0.15,
        redemption_bonus=0.1
    )
    
    # Results storage
    all_results = {}
    
    # Test each protocol
    protocols = [
        ("P1_Evidence_First", P1EvidenceFirstProtocol()),
        ("P2_Cross_Exam", P2CrossExamProtocol(num_cross_exam_questions=2)),
        ("P3_Slashing", P3SlashingProtocol(
            num_cross_exam_questions=2,
            reputation_config=reputation_config,
            reputation_store=ReputationStore("data/reputation_test.db")
        ))
    ]
    
    deviation_types = ["honest", "lie", "withhold", "persuasion_only"]
    
    for protocol_name, protocol in protocols:
        print("\n" + "="*80)
        print(f"TESTING: {protocol_name}")
        print("="*80)
        
        # Initialize components
        print(f"\n[1/4] Initializing dataset...")
        dataset_repo = HFFEVERRepository(
            split="dev",  # FEVER uses 'dev' not 'validation'
            num_samples=10,
            seed=42
        )
        
        print(f"[2/4] Initializing verifier...")
        verifier = FEVERGroundTruthVerifier(use_semantic_matching=False)
        
        print(f"[3/4] Initializing storage...")
        storage_path = f"results/milestone4/{protocol_name.lower()}_episodes.jsonl"
        storage = JSONLStorage(filepath=storage_path)
        
        print(f"[4/4] Running deviation suite...")
        
        # Run episode
        run_episode = RunEpisode(
            protocol=protocol,
            verifier=verifier,
            model_name="gpt-4o-mini",
            api_key=api_key,
            lambda_cost=0.01,
            mu_penalty=0.5
        )
        
        # Deviation suite
        deviation_suite = RunDeviationSuite(
            run_episode=run_episode,
            dataset_repo=dataset_repo,
            storage=storage,
            num_tasks=10,
            deviation_types=deviation_types,
            payoff_config=payoff_config
        )
        
        try:
            results = deviation_suite.execute_sync()
            all_results[protocol_name] = results
            
            print(f"\n✓ {protocol_name} complete")
            print(f"  IRI: {results['iri']:.3f}")
            
        except Exception as e:
            print(f"\n❌ Error testing {protocol_name}: {e}")
            import traceback
            traceback.print_exc()
    
    # Print comparison
    print("\n" + "="*80)
    print("PROTOCOL PROGRESSION ANALYSIS")
    print("="*80)
    
    print(f"\n{'Protocol':<20} {'IRI':>10} {'Status':<20}")
    print("-"*50)
    
    for protocol_name, results in all_results.items():
        iri = results['iri']
        
        if iri < 0.05:
            status = "✓✓ Excellent"
        elif iri < 0.15:
            status = "✓ Good"
        else:
            status = "○ Moderate"
        
        print(f"{protocol_name:<20} {iri:>10.3f} {status:<20}")
    
    # Check progression
    print("\n📊 PROGRESSION CHECK:")
    iri_values = [results['iri'] for results in all_results.values()]
    
    if len(iri_values) >= 2:
        if iri_values[-1] < iri_values[0]:
            improvement = ((iri_values[0] - iri_values[-1]) / iri_values[0]) * 100
            print(f"  ✓ P3 improved {improvement:.1f}% over P1")
        else:
            print(f"  ⚠ No clear progression detected")
    
    # Reputation summary (for P3)
    if "P3_Slashing" in all_results:
        print("\n📈 REPUTATION SUMMARY (P3):")
        p3_protocol = protocols[2][1]  # P3 protocol instance
        p3_protocol.print_reputation_summary()
    
    # Save combined results
    import json
    output_path = "results/milestone4/protocol_comparison.json"
    os.makedirs("results/milestone4", exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    print("\n" + "="*80)
    print("✅ MILESTONE 4 COMPLETE")
    print("="*80)
    print(f"\nResults saved to: {output_path}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
