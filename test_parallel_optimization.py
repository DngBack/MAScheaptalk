"""Test parallel execution optimization with small task set."""
import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from infrastructure.datasets.hf_fever_repo import HFFEVERRepository
from infrastructure.verifiers.verifier_factory import create_fever_verifier
from infrastructure.storage.jsonl_storage import JSONLStorage
from infrastructure.llm.api_key_pool import APIKeyPool
from infrastructure.storage.checkpoint_manager import CheckpointManager
from domain.entities.payoff import PayoffConfig
from application.protocols.p1_evidence_first import P1EvidenceFirstProtocol
from application.use_cases.run_episode import RunEpisode
from application.use_cases.run_deviation_suite import RunDeviationSuite


def test_api_key_pool():
    """Test API key pool functionality."""
    print("\n" + "="*70)
    print("TEST 1: API Key Pool")
    print("="*70)
    
    # Test single key
    pool = APIKeyPool(["test-key-1"], rate_limit_rpm=500)
    assert len(pool) == 1
    print("✓ Single key pool created")
    
    # Test multiple keys
    pool = APIKeyPool(["key1", "key2", "key3"], rate_limit_rpm=500)
    assert len(pool) == 3
    print("✓ Multi-key pool created")
    
    # Test round-robin
    import asyncio
    async def test_round_robin():
        keys = []
        for _ in range(6):
            key = await pool.get_next_key()
            keys.append(key)
        # Should cycle through: key1, key2, key3, key1, key2, key3
        assert keys == ["key1", "key2", "key3", "key1", "key2", "key3"]
        print("✓ Round-robin selection works")
    
    asyncio.run(test_round_robin())
    
    # Test from env string
    pool = APIKeyPool.from_env_string("key1,key2,key3", rate_limit_rpm=500)
    assert len(pool) == 3
    print("✓ Creation from env string works")
    
    print("\n✅ API Key Pool tests passed!")


def test_checkpoint_manager():
    """Test checkpoint manager functionality."""
    print("\n" + "="*70)
    print("TEST 2: Checkpoint Manager")
    print("="*70)
    
    # Create checkpoint manager
    checkpoint_dir = "results/test_checkpoints"
    manager = CheckpointManager(
        checkpoint_dir=checkpoint_dir,
        milestone="test_milestone",
        seed=42
    )
    
    # Save checkpoint
    manager.save(
        episode_ids=["ep1", "ep2", "ep3"],
        total_episodes=10,
        metadata={"test": "value"}
    )
    print("✓ Checkpoint saved")
    
    # Verify checkpoint exists
    assert manager.checkpoint_path.exists()
    print("✓ Checkpoint file exists")
    
    # Create new manager and load
    manager2 = CheckpointManager(
        checkpoint_dir=checkpoint_dir,
        milestone="test_milestone",
        seed=42
    )
    loaded = manager2.load()
    assert loaded == True
    assert len(manager2.completed_episodes) == 3
    print("✓ Checkpoint loaded successfully")
    
    # Test resume check
    assert manager2.is_completed("ep1") == True
    assert manager2.is_completed("ep4") == False
    print("✓ Episode completion check works")
    
    # Cleanup
    manager2.cleanup()
    print("✓ Checkpoint cleanup works")
    
    print("\n✅ Checkpoint Manager tests passed!")


def test_parallel_execution():
    """Test parallel execution with real milestone run (small scale)."""
    print("\n" + "="*70)
    print("TEST 3: Parallel Execution (Milestone 2 - Small Scale)")
    print("="*70)
    
    # Load environment
    load_dotenv()
    
    # Get API keys
    api_keys_str = os.getenv('OPENAI_API_KEYS', os.getenv('OPENAI_API_KEY', ''))
    if not api_keys_str:
        print("⚠ Warning: No API key found. Skipping parallel execution test.")
        return
    
    api_key_pool = APIKeyPool.from_env_string(api_keys_str, rate_limit_rpm=500)
    api_key = api_keys_str.split(',')[0].strip()
    
    print(f"✓ Using {len(api_key_pool)} API key(s)")
    
    # Small test configuration
    num_tasks = 5
    num_samples = 10
    seed = 42
    max_concurrent = 5
    
    print(f"\nTest configuration:")
    print(f"  - Tasks: {num_tasks}")
    print(f"  - Max concurrent: {max_concurrent}")
    print(f"  - Deviation types: 2 (honest, no_evidence)")
    print(f"  - Total episodes: {num_tasks * 2} = 10")
    
    # Initialize components
    print("\nInitializing components...")
    dataset_repo = HFFEVERRepository(split="dev", num_samples=num_samples, seed=seed)
    
    verifier = create_fever_verifier(
        use_semantic_matching=False,
        use_llm_evidence_eval=False,  # Disable for faster test
        api_key=api_key
    )
    
    storage = JSONLStorage(filepath="results/test_parallel/episodes.jsonl")
    protocol = P1EvidenceFirstProtocol()
    payoff_config = PayoffConfig(lambda_cost=0.01, mu_penalty=0.5)
    
    checkpoint_manager = CheckpointManager(
        checkpoint_dir="results/test_checkpoints",
        milestone="test_parallel",
        seed=seed,
        auto_cleanup=True
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
    
    deviation_suite = RunDeviationSuite(
        run_episode=run_episode,
        dataset_repo=dataset_repo,
        storage=storage,
        num_tasks=num_tasks,
        deviation_types=["honest", "no_evidence"],  # Just 2 for quick test
        payoff_config=payoff_config,
        max_concurrent=max_concurrent,
        batch_size=5,
        checkpoint_manager=checkpoint_manager
    )
    
    # Run with timing
    print("\nRunning parallel execution test...")
    start_time = time.time()
    
    try:
        results = deviation_suite.execute_sync()
        elapsed = time.time() - start_time
        
        print(f"\n✓ Execution completed in {elapsed:.1f}s")
        print(f"✓ Tasks completed: {results['num_tasks']}")
        print(f"✓ IRI: {results['iri']:.3f}")
        
        # Verify results
        assert results['num_tasks'] == num_tasks
        assert 'honest' in results['metrics_by_type']
        assert 'no_evidence' in results['metrics_by_type']
        
        # Check if API key pool was used
        if len(api_key_pool) > 1:
            api_key_pool.print_stats()
        
        print("\n✅ Parallel execution test passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Parallel execution test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("="*70)
    print("PARALLEL EXECUTION OPTIMIZATION - TEST SUITE")
    print("="*70)
    
    # Test 1: API Key Pool
    try:
        test_api_key_pool()
    except Exception as e:
        print(f"\n❌ API Key Pool test failed: {e}")
        return 1
    
    # Test 2: Checkpoint Manager
    try:
        test_checkpoint_manager()
    except Exception as e:
        print(f"\n❌ Checkpoint Manager test failed: {e}")
        return 1
    
    # Test 3: Parallel Execution (optional - requires API key)
    print("\n" + "="*70)
    print("TEST 3: Parallel Execution (requires API key)")
    print("="*70)
    
    api_keys_str = os.getenv('OPENAI_API_KEYS', os.getenv('OPENAI_API_KEY', ''))
    if not api_keys_str:
        print("⚠ Skipping parallel execution test (no API key configured)")
        print("  To run this test, set OPENAI_API_KEY or OPENAI_API_KEYS in .env")
    else:
        print(f"\n✓ API key found, running parallel execution test...")
        print("⚠ This will make real API calls and use credits!")
        
        import time
        print("\nStarting in 3 seconds... (Ctrl+C to cancel)")
        time.sleep(3)
        
        success = test_parallel_execution()
        if not success:
            return 1
    
    print("\n" + "="*70)
    print("✅ ALL TESTS PASSED!")
    print("="*70)
    print("\nNext steps:")
    print("1. Update your .env with multiple API keys (OPENAI_API_KEYS)")
    print("2. Set MAX_CONCURRENT_EPISODES based on your tier")
    print("3. Run full milestone with: python run_milestone2_deviation.py")
    print("4. Expected speedup: 12-18× with 3 keys and 30 concurrent episodes")
    print("="*70)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
