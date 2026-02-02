"""Run all milestones sequentially to get complete results."""
import sys
import subprocess
from pathlib import Path


def run_script(script_name: str, description: str) -> bool:
    """Run a Python script and return success status."""
    print("\n" + "="*80)
    print(f"RUNNING: {description}")
    print("="*80)
    
    try:
        result = subprocess.run(
            [sys.executable, script_name],
            check=True,
            capture_output=False
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Failed to run {script_name}")
        return False


def main():
    """Run all milestones."""
    
    print("="*80)
    print("COMPLETE MILESTONE EXECUTION")
    print("="*80)
    print("\nThis will run all three milestones:")
    print("  1. Milestone 2: Deviation Suite")
    print("  2. Milestone 3: Baseline Comparison")
    print("  3. Milestone 4: Protocol Progression (P1→P2→P3)")
    print("\nEstimated time: 5-10 minutes (with mock LLM)")
    print("="*80)
    
    input("\nPress Enter to continue or Ctrl+C to cancel...")
    
    # Track results
    results = []
    
    # Milestone 2
    success = run_script(
        "run_milestone2_deviation.py",
        "Milestone 2: Deviation Suite"
    )
    results.append(("Milestone 2", success))
    
    if not success:
        print("\n⚠ Milestone 2 failed, continuing anyway...")
    
    # Milestone 3
    success = run_script(
        "run_milestone3_baselines.py",
        "Milestone 3: Baseline Comparison"
    )
    results.append(("Milestone 3", success))
    
    if not success:
        print("\n⚠ Milestone 3 failed, continuing anyway...")
    
    # Milestone 4
    success = run_script(
        "run_milestone4_protocols.py",
        "Milestone 4: Protocol Progression"
    )
    results.append(("Milestone 4", success))
    
    # Summary
    print("\n" + "="*80)
    print("EXECUTION SUMMARY")
    print("="*80)
    
    for milestone, success in results:
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"  {milestone:<20} {status}")
    
    # Results location
    print("\n📁 RESULTS LOCATION:")
    print("  - Milestone 2: results/milestone2/")
    print("  - Milestone 3: results/milestone3/")
    print("  - Milestone 4: results/milestone4/")
    
    print("\n📊 KEY FILES:")
    print("  - Deviation Suite: results/milestone2/deviation_suite_results.json")
    print("  - Baseline Comparison: results/milestone3/baseline_comparison.json")
    print("  - Protocol Comparison: results/milestone4/protocol_comparison.json")
    
    print("\n" + "="*80)
    
    # Check if all succeeded
    all_success = all(success for _, success in results)
    
    if all_success:
        print("✅ ALL MILESTONES COMPLETED SUCCESSFULLY!")
        print("\nYou now have complete results for your paper:")
        print("  ✓ Deviation Gain (DG) analysis")
        print("  ✓ Incentive Robustness Index (IRI)")
        print("  ✓ Baseline comparison")
        print("  ✓ Protocol progression (P1→P2→P3)")
        return 0
    else:
        print("⚠ Some milestones failed. Check logs above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
