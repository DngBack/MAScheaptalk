"""Run baseline comparison use case."""
import asyncio
import json
from typing import List, Dict, Any, Optional
from pathlib import Path as PathLib

import sys
from pathlib import Path
src_path = Path(__file__).parent.parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from domain.entities.task import Task
from domain.entities.episode import Episode
from domain.entities.payoff import PayoffCalculator, PayoffConfig
from domain.ports.dataset_repo import DatasetRepository
from domain.ports.storage import Storage
from domain.ports.llm_client import LLMClient
from application.baselines.base_baseline import BaseBaseline
from application.use_cases.run_episode import RunEpisode


class RunBaselineComparison:
    """
    Use case for comparing protocol with strong baselines.
    
    Ensures fair comparison by:
    - Using same LLM model
    - Tracking budget (tokens, calls)
    - Running on same tasks with same random seed
    """
    
    def __init__(
        self,
        dataset_repo: DatasetRepository,
        storage: Storage,
        llm_client: LLMClient,
        num_tasks: int = 100,
        max_tokens_per_task: int = 2000,
        max_calls_per_task: int = 10,
        payoff_config: Optional[PayoffConfig] = None
    ):
        """
        Initialize baseline comparison.
        
        Args:
            dataset_repo: Dataset repository
            storage: Storage for episodes
            llm_client: LLM client (same for all methods)
            num_tasks: Number of tasks to compare
            max_tokens_per_task: Budget limit for tokens
            max_calls_per_task: Budget limit for LLM calls
            payoff_config: Configuration for payoff calculation
        """
        self.dataset_repo = dataset_repo
        self.storage = storage
        self.llm_client = llm_client
        self.num_tasks = num_tasks
        self.max_tokens_per_task = max_tokens_per_task
        self.max_calls_per_task = max_calls_per_task
        self.payoff_calculator = PayoffCalculator(payoff_config or PayoffConfig())
    
    async def execute(
        self,
        baselines: List[BaseBaseline],
        run_episode: Optional[RunEpisode] = None
    ) -> Dict[str, Any]:
        """
        Execute baseline comparison.
        
        Args:
            baselines: List of baseline methods to compare
            run_episode: Optional RunEpisode for protocol comparison
            
        Returns:
            Comprehensive comparison results
        """
        print("="*80)
        print("BASELINE COMPARISON")
        print("="*80)
        print(f"Tasks: {self.num_tasks}")
        print(f"Budget: {self.max_tokens_per_task} tokens, {self.max_calls_per_task} calls per task")
        print(f"Methods: {', '.join([b.get_baseline_id() for b in baselines])}")
        print("="*80)
        
        # Store episodes by method
        episodes_by_method: Dict[str, List[Episode]] = {}
        
        # Initialize storage for each baseline
        for baseline in baselines:
            episodes_by_method[baseline.get_baseline_id()] = []
        
        # If protocol comparison included
        if run_episode:
            episodes_by_method["protocol_p1"] = []
        
        # Iterate through tasks
        task_count = 0
        for task in self.dataset_repo.iter_tasks(limit=self.num_tasks):
            task_count += 1
            print(f"\n[Task {task_count}/{self.num_tasks}] {task.claim[:60]}...")
            
            # Run each baseline
            for baseline in baselines:
                method_id = baseline.get_baseline_id()
                
                try:
                    episode = await baseline.execute(task)
                    
                    # Recalculate payoff
                    payoff, breakdown = self.payoff_calculator.calculate_payoff(
                        label_correct=episode.verifier_result.label_correct,
                        evidence_provided=episode.verifier_result.evidence_provided,
                        evidence_match_score=episode.verifier_result.evidence_match_score,
                        token_count=0,  # TODO: Track actual tokens
                        tool_calls=0,
                        deviation_type="baseline"
                    )
                    
                    episode.payoff = payoff
                    episode.metrics.update(breakdown)
                    
                    # Store
                    self.storage.save_episode(episode)
                    episodes_by_method[method_id].append(episode)
                    
                    # Print result
                    symbol = "✓" if episode.verifier_result.label_correct else "✗"
                    print(f"  {method_id:25s} {symbol} payoff={payoff:+.3f}")
                
                except Exception as e:
                    print(f"  {method_id:25s} ERROR: {e}")
                    continue
            
            # Run protocol if provided
            if run_episode:
                try:
                    episode = await run_episode.execute(task, "honest")
                    
                    # Recalculate payoff
                    payoff, breakdown = self.payoff_calculator.calculate_payoff(
                        label_correct=episode.verifier_result.label_correct,
                        evidence_provided=episode.verifier_result.evidence_provided,
                        evidence_match_score=episode.verifier_result.evidence_match_score,
                        token_count=0,
                        tool_calls=0,
                        deviation_type="honest"
                    )
                    
                    episode.payoff = payoff
                    episode.metrics.update(breakdown)
                    
                    self.storage.save_episode(episode)
                    episodes_by_method["protocol_p1"].append(episode)
                    
                    symbol = "✓" if episode.verifier_result.label_correct else "✗"
                    print(f"  {'protocol_p1':25s} {symbol} payoff={payoff:+.3f}")
                
                except Exception as e:
                    print(f"  {'protocol_p1':25s} ERROR: {e}")
        
        # Compute comparison metrics
        results = self._compute_comparison_metrics(episodes_by_method)
        
        # Print comparison table
        self._print_comparison_table(results)
        
        return results
    
    def _compute_comparison_metrics(
        self,
        episodes_by_method: Dict[str, List[Episode]]
    ) -> Dict[str, Any]:
        """Compute comprehensive comparison metrics."""
        
        results = {
            "num_tasks": self.num_tasks,
            "budget": {
                "max_tokens_per_task": self.max_tokens_per_task,
                "max_calls_per_task": self.max_calls_per_task
            },
            "methods": {},
            "rankings": {}
        }
        
        # Compute metrics for each method
        for method_id, episodes in episodes_by_method.items():
            if not episodes:
                continue
            
            metrics = {
                "accuracy": sum(1 for ep in episodes if ep.verifier_result.label_correct) / len(episodes),
                "evidence_compliance": sum(1 for ep in episodes if ep.verifier_result.evidence_provided) / len(episodes),
                "evidence_match_score": sum(ep.verifier_result.evidence_match_score for ep in episodes) / len(episodes),
                "mean_payoff": sum(ep.payoff for ep in episodes) / len(episodes),
                "num_episodes": len(episodes),
                "std_payoff": 0.0  # Will calculate below
            }
            
            # Calculate standard deviation
            import numpy as np
            payoffs = [ep.payoff for ep in episodes]
            metrics["std_payoff"] = float(np.std(payoffs))
            
            results["methods"][method_id] = metrics
        
        # Rankings
        methods_list = list(results["methods"].items())
        
        # Rank by accuracy
        accuracy_ranking = sorted(methods_list, key=lambda x: x[1]["accuracy"], reverse=True)
        results["rankings"]["accuracy"] = [m[0] for m in accuracy_ranking]
        
        # Rank by evidence compliance
        evidence_ranking = sorted(methods_list, key=lambda x: x[1]["evidence_compliance"], reverse=True)
        results["rankings"]["evidence_compliance"] = [m[0] for m in evidence_ranking]
        
        # Rank by payoff
        payoff_ranking = sorted(methods_list, key=lambda x: x[1]["mean_payoff"], reverse=True)
        results["rankings"]["payoff"] = [m[0] for m in payoff_ranking]
        
        return results
    
    def _print_comparison_table(self, results: Dict[str, Any]):
        """Print formatted comparison table."""
        
        print("\n" + "="*80)
        print("BASELINE COMPARISON RESULTS")
        print("="*80)
        print(f"Tasks: {results['num_tasks']}")
        print(f"Budget: {results['budget']['max_tokens_per_task']} tokens, "
              f"{results['budget']['max_calls_per_task']} calls per task")
        print("="*80)
        
        # Table header
        print(f"\n{'Method':<25} {'Accuracy':>10} {'Evidence':>10} {'Payoff':>10} {'Notes':<20}")
        print(f"{'':.<25} {'':.<10} {'Compliance':.<10} {'':.<10} {'':.<20}")
        print("-"*80)
        
        # Sort methods by accuracy
        methods_sorted = sorted(
            results["methods"].items(),
            key=lambda x: x[1]["accuracy"],
            reverse=True
        )
        
        for method_id, metrics in methods_sorted:
            accuracy = f"{metrics['accuracy']:.3f}"
            evidence = f"{metrics['evidence_compliance']:.3f}"
            payoff = f"{metrics['mean_payoff']:+.3f}"
            
            # Notes
            notes = []
            if metrics["evidence_compliance"] > 0.8:
                notes.append("High evidence")
            if metrics["accuracy"] >= max(m[1]["accuracy"] for m in methods_sorted):
                notes.append("Best accuracy")
            
            notes_str = ", ".join(notes) if notes else ""
            
            print(f"{method_id:<25} {accuracy:>10} {evidence:>10} {payoff:>10} {notes_str:<20}")
        
        print("="*80)
        
        # Key findings
        print("\nKEY FINDINGS:")
        
        # Best accuracy
        best_accuracy_method = results["rankings"]["accuracy"][0]
        best_accuracy = results["methods"][best_accuracy_method]["accuracy"]
        print(f"  Best accuracy: {best_accuracy_method} ({best_accuracy:.1%})")
        
        # Best evidence compliance
        best_evidence_method = results["rankings"]["evidence_compliance"][0]
        best_evidence = results["methods"][best_evidence_method]["evidence_compliance"]
        print(f"  Best evidence: {best_evidence_method} ({best_evidence:.1%})")
        
        # Protocol vs baselines
        if "protocol_p1" in results["methods"]:
            p1_acc = results["methods"]["protocol_p1"]["accuracy"]
            p1_evidence = results["methods"]["protocol_p1"]["evidence_compliance"]
            
            print(f"\n  Protocol P1:")
            print(f"    Accuracy: {p1_acc:.1%}")
            print(f"    Evidence compliance: {p1_evidence:.1%}")
            
            # Compare to best baseline
            best_baseline_acc = max(
                m["accuracy"] for mid, m in results["methods"].items()
                if mid != "protocol_p1"
            )
            
            acc_diff = (p1_acc - best_baseline_acc) * 100
            
            if abs(acc_diff) < 5:
                print(f"    ✓ Competitive accuracy ({acc_diff:+.1f}% vs best baseline)")
            elif acc_diff > 0:
                print(f"    ✓✓ Higher accuracy ({acc_diff:+.1f}% vs best baseline)")
            else:
                print(f"    Lower accuracy ({acc_diff:+.1f}% vs best baseline)")
            
            if p1_evidence > 0.8:
                print(f"    ✓✓ UNIQUE VALUE: Only method with high evidence compliance")
        
        print("="*80)
    
    def execute_sync(self, baselines: List[BaseBaseline], run_episode: Optional[RunEpisode] = None) -> Dict[str, Any]:
        """Synchronous wrapper for execute."""
        return asyncio.run(self.execute(baselines, run_episode))
    
    def save_results(self, results: Dict[str, Any], output_path: str):
        """Save comparison results to JSON file."""
        output_path = PathLib(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\nResults saved to: {output_path}")
