#!/usr/bin/env python3
"""Quick validation script to check if the setup is working."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")
    
    try:
        from domain.entities.task import Task
        from domain.entities.episode import Episode
        from domain.value_objects.labels import FEVERLabel
        from domain.value_objects.role import AgentRole
        print("  ✓ Domain entities")
        
        from domain.ports.llm_client import LLMClient
        from domain.ports.dataset_repo import DatasetRepository
        from domain.ports.verifier import Verifier
        from domain.ports.storage import Storage
        print("  ✓ Domain ports")
        
        from application.protocols.p1_evidence_first import P1EvidenceFirstProtocol
        print("  ✓ Protocols")
        
        from application.use_cases.run_episode import RunEpisode
        from application.use_cases.run_experiment import RunExperiment
        print("  ✓ Use cases")
        
        from application.scoring.fever_scoring import FEVERScoring
        print("  ✓ Scoring")
        
        from infrastructure.datasets.hf_fever_repo import HFFEVERRepository
        from infrastructure.verifiers.fever_groundtruth_verifier import FEVERGroundTruthVerifier
        from infrastructure.storage.jsonl_storage import JSONLStorage
        print("  ✓ Infrastructure")
        
        print("\nAll imports successful! ✓")
        return True
        
    except ImportError as e:
        print(f"\n✗ Import failed: {e}")
        return False


def test_dataset_loading():
    """Test loading FEVER dataset."""
    print("\nTesting FEVER dataset loading...")
    
    try:
        from infrastructure.datasets.hf_fever_repo import HFFEVERRepository
        
        print("  Loading 5 samples from FEVER...")
        repo = HFFEVERRepository(split="validation", num_samples=5, seed=42)
        
        task = repo.get_task(0)
        print(f"  ✓ Loaded task: {task.task_id}")
        print(f"    Claim: {task.claim[:60]}...")
        print(f"    Label: {task.label}")
        print(f"    Evidence count: {len(task.evidence)}")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Dataset loading failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_protocol():
    """Test protocol initialization."""
    print("\nTesting P1 protocol...")
    
    try:
        from application.protocols.p1_evidence_first import P1EvidenceFirstProtocol
        
        protocol = P1EvidenceFirstProtocol()
        
        honest_prompt = protocol.get_sender_system_prompt("honest")
        no_evidence_prompt = protocol.get_sender_system_prompt("no_evidence")
        receiver_prompt = protocol.get_receiver_system_prompt()
        
        print(f"  ✓ Protocol ID: {protocol.get_protocol_id()}")
        print(f"  ✓ Honest sender prompt length: {len(honest_prompt)} chars")
        print(f"  ✓ No-evidence sender prompt length: {len(no_evidence_prompt)} chars")
        print(f"  ✓ Receiver prompt length: {len(receiver_prompt)} chars")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Protocol test failed: {e}")
        return False


def main():
    """Run all validation tests."""
    print("="*60)
    print("SETUP VALIDATION")
    print("="*60)
    
    results = []
    
    results.append(("Imports", test_imports()))
    results.append(("FEVER Dataset", test_dataset_loading()))
    results.append(("P1 Protocol", test_protocol()))
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    for name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{name:20s}: {status}")
    
    all_passed = all(success for _, success in results)
    
    if all_passed:
        print("\n✓ All validation checks passed!")
        print("\nYou can now run the experiment:")
        print("  python src/interfaces/cli/main.py")
    else:
        print("\n✗ Some validation checks failed.")
        print("Please fix the issues before running the experiment.")
        sys.exit(1)


if __name__ == "__main__":
    main()
