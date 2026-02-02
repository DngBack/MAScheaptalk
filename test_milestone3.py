"""Quick test for Milestone 3 with better error handling."""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

def main():
    """Test Milestone 3."""
    
    # Load environment
    load_dotenv()
    
    print("="*80)
    print("MILESTONE 3: BASELINE COMPARISON (DEBUG)")
    print("="*80)
    
    # Check API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("\n❌ OPENAI_API_KEY not set!")
        print("Please run: export OPENAI_API_KEY=your-key")
        return 1
    
    print(f"✅ API key found: {api_key[:10]}...{api_key[-4:]}")
    
    # Test imports
    print("\n[1/7] Testing imports...")
    try:
        from infrastructure.datasets.hf_fever_repo import HFFEVERRepository
        print("  ✓ Dataset import OK")
        
        from infrastructure.llm.openai_client import OpenAIClient
        print("  ✓ OpenAI client import OK")
        
        from application.baselines.self_consistency import SelfConsistency
        print("  ✓ Self-Consistency import OK")
        
        from application.baselines.self_refine import SelfRefine
        print("  ✓ Self-Refine import OK")
        
        from application.use_cases.run_baseline_comparison import RunBaselineComparison
        print("  ✓ Baseline comparison import OK")
        
    except ImportError as e:
        print(f"  ❌ Import error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Initialize components
    print("\n[2/7] Initializing dataset (2 tasks only)...")
    try:
        dataset_repo = HFFEVERRepository(split="train", num_samples=2, seed=42)
        print(f"  ✓ Loaded {dataset_repo.get_num_tasks()} tasks")
    except Exception as e:
        print(f"  ❌ Dataset error: {e}")
        return 1
    
    print("\n[3/7] Initializing LLM client...")
    try:
        llm_client = OpenAIClient(model="gpt-4o-mini", api_key=api_key)
        print(f"  ✓ OpenAI client ready (model: gpt-4o-mini)")
    except Exception as e:
        print(f"  ❌ LLM client error: {e}")
        return 1
    
    print("\n[4/7] Testing API connection...")
    try:
        test_response = llm_client.generate_with_usage(
            messages=[{"role": "user", "content": "Say 'test' in one word"}],
            temperature=0,
            max_tokens=5
        )
        print(f"  ✓ API working! Response: {test_response['content'][:50]}")
        print(f"  ✓ Tokens used: {test_response['usage']['total_tokens']}")
    except Exception as e:
        print(f"  ❌ API error: {e}")
        return 1
    
    print("\n[5/7] Creating baselines...")
    try:
        self_consistency = SelfConsistency(
            llm_client=llm_client,
            k_samples=3,  # Small for testing
            temperature=0.7
        )
        print(f"  ✓ Self-Consistency created (K=3)")
        
        self_refine = SelfRefine(
            llm_client=llm_client,
            num_rounds=1,  # Small for testing
            temperature=0.3
        )
        print(f"  ✓ Self-Refine created (rounds=1)")
        
    except Exception as e:
        print(f"  ❌ Baseline creation error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    print("\n[6/7] Testing Self-Consistency on 1 task...")
    try:
        task = dataset_repo.get_task(0)
        print(f"  Task: {task.claim[:60]}...")
        
        episode = self_consistency.execute_sync(task)
        print(f"  ✓ Prediction: {episode.verifier_result.predicted_label}")
        print(f"  ✓ Correct: {episode.verifier_result.label_correct}")
        
    except Exception as e:
        print(f"  ❌ Execution error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    print("\n[7/7] Testing Self-Refine on 1 task...")
    try:
        episode = self_refine.execute_sync(task)
        print(f"  ✓ Prediction: {episode.verifier_result.predicted_label}")
        print(f"  ✓ Correct: {episode.verifier_result.label_correct}")
        
    except Exception as e:
        print(f"  ❌ Execution error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    print("\n" + "="*80)
    print("✅ ALL TESTS PASSED!")
    print("="*80)
    print("\nMilestone 3 is ready to run with:")
    print("  python run_milestone3_baselines.py")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
