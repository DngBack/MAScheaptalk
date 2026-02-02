"""Run deviation suite use case for systematic deviation testing."""
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
from application.use_cases.run_episode import RunEpisode
from application.protocols.deviation_policies import DeviationPolicy


class RunDeviationSuite:
    """
    Use case for running comprehensive deviation tests.
    
    This systematically tests all deviation types against the protocol
    to measure deviation gain (DG) and validate protocol effectiveness.
    """
    
    def __init__(
        self,
        run_episode: RunEpisode,
        dataset_repo: DatasetRepository,
        storage: Storage,
        num_tasks: int = 100,
        deviation_types: Optional[List[str]] = None,
        payoff_config: Optional[PayoffConfig] = None
    ):
        """
        Initialize deviation suite.
        
        Args:
            run_episode: RunEpisode use case instance
            dataset_repo: Dataset repository
            storage: Storage for episodes
            num_tasks: Number of tasks to test
            deviation_types: List of deviation types (defaults to all)
            payoff_config: Configuration for payoff calculation
        """
        self.run_episode = run_episode
        self.dataset_repo = dataset_repo
        self.storage = storage
        self.num_tasks = num_tasks
        
        # Default to all deviation types
        if deviation_types is None:
            self.deviation_types = DeviationPolicy.get_all_deviation_types()
        else:
            self.deviation_types = deviation_types
        
        self.payoff_calculator = PayoffCalculator(payoff_config or PayoffConfig())
    
    async def execute(self) -> Dict[str, Any]:
        """
        Execute the deviation suite.
        
        For each task:
        1. Run with honest behavior
        2. Run with each deviation type
        3. Calculate deviation gain for each deviation
        
        Returns:
            Dictionary with comprehensive deviation analysis
        """
        print("="*70)
        print("DEVIATION SUITE ANALYSIS")
        print("="*70)
        print(f"Tasks: {self.num_tasks}")
        print(f"Deviation types: {', '.join(self.deviation_types)}")
        print(f"Payoff config: λ={self.payoff_calculator.config.lambda_cost}, "
              f"μ={self.payoff_calculator.config.mu_penalty}")
        print("="*70)
        
        # Store episodes by deviation type
        episodes_by_type: Dict[str, List[Episode]] = {
            dt: [] for dt in self.deviation_types
        }
        
        # Iterate through tasks
        task_count = 0
        for task in self.dataset_repo.iter_tasks(limit=self.num_tasks):
            task_count += 1
            print(f"\n[Task {task_count}/{self.num_tasks}] {task.task_id}: {task.claim[:60]}...")
            
            # Run episode for each deviation type
            for deviation_type in self.deviation_types:
                try:
                    episode = await self.run_episode.execute(task, deviation_type)
                    
                    # Recalculate payoff using our payoff calculator
                    payoff, breakdown = self.payoff_calculator.calculate_payoff(
                        label_correct=episode.verifier_result.label_correct,
                        evidence_provided=episode.verifier_result.evidence_provided,
                        evidence_match_score=episode.verifier_result.evidence_match_score,
                        token_count=0,  # TODO: Track tokens
                        tool_calls=0,   # TODO: Track tool calls
                        deviation_type=deviation_type
                    )
                    
                    # Update episode with new payoff
                    episode.payoff = payoff
                    episode.metrics.update(breakdown)
                    
                    # Store episode
                    self.storage.save_episode(episode)
                    episodes_by_type[deviation_type].append(episode)
                    
                    # Print concise result
                    symbol = "✓" if episode.verifier_result.label_correct else "✗"
                    print(f"  {deviation_type:15s} {symbol} payoff={payoff:+.3f}")
                
                except Exception as e:
                    print(f"  {deviation_type:15s} ERROR: {e}")
                    continue
        
        # Compute comprehensive metrics
        results = self._compute_comprehensive_metrics(episodes_by_type)
        
        # Print detailed analysis
        self._print_deviation_analysis(results)
        
        return results
    
    def _compute_comprehensive_metrics(
        self,
        episodes_by_type: Dict[str, List[Episode]]
    ) -> Dict[str, Any]:
        """Compute comprehensive deviation metrics."""
        
        results = {
            "num_tasks": len(episodes_by_type.get("honest", [])),
            "deviation_types": self.deviation_types,
            "payoff_config": self.payoff_calculator.config.to_dict(),
            "metrics_by_type": {},
            "deviation_gains": {},
            "iri": 0.0
        }
        
        # Get honest episodes as baseline
        honest_episodes = episodes_by_type.get("honest", [])
        if not honest_episodes:
            print("WARNING: No honest episodes found!")
            return results
        
        honest_payoffs = [ep.payoff for ep in honest_episodes]
        
        # Compute metrics for each deviation type
        for deviation_type, episodes in episodes_by_type.items():
            if not episodes:
                continue
            
            # Basic metrics
            metrics = {
                "accuracy": sum(1 for ep in episodes if ep.verifier_result.label_correct) / len(episodes),
                "evidence_compliance": sum(1 for ep in episodes if ep.verifier_result.evidence_provided) / len(episodes),
                "evidence_match_score": sum(ep.verifier_result.evidence_match_score for ep in episodes) / len(episodes),
                "mean_payoff": sum(ep.payoff for ep in episodes) / len(episodes),
                "num_episodes": len(episodes)
            }
            
            results["metrics_by_type"][deviation_type] = metrics
            
            # Calculate deviation gain (if not honest)
            if deviation_type != "honest":
                deviation_payoffs = [ep.payoff for ep in episodes]
                dg_stats = self.payoff_calculator.calculate_deviation_gain(
                    honest_payoffs, deviation_payoffs
                )
                results["deviation_gains"][deviation_type] = dg_stats
        
        # Calculate Incentive Robustness Index (IRI)
        dg_values = {
            dt: stats["deviation_gain"]
            for dt, stats in results["deviation_gains"].items()
        }
        results["iri"] = self.payoff_calculator.calculate_iri(dg_values)
        
        return results
    
    def _print_deviation_analysis(self, results: Dict[str, Any]):
        """Print detailed deviation analysis."""
        
        print("\n" + "="*70)
        print("DEVIATION GAIN ANALYSIS")
        print("="*70)
        
        if not results["deviation_gains"]:
            print("No deviation gains to report.")
            return
        
        for deviation_type, dg_stats in results["deviation_gains"].items():
            dg = dg_stats["deviation_gain"]
            pct_positive = dg_stats["percent_dg_positive"]
            
            # Determine effectiveness
            if dg < -0.3:
                effectiveness = "✓✓ Very effective"
            elif dg < 0:
                effectiveness = "✓ Effective"
            elif dg < 0.1:
                effectiveness = "⚠ Weak"
            else:
                effectiveness = "✗ Ineffective"
            
            print(f"\n{deviation_type.upper()} vs honest:")
            print(f"  Deviation Gain:        {dg:+.3f}")
            print(f"  % episodes DG > 0:     {pct_positive:.1f}%")
            print(f"  Honest mean payoff:    {dg_stats['honest_mean']:+.3f}")
            print(f"  Deviation mean payoff: {dg_stats['deviation_mean']:+.3f}")
            print(f"  Status:                {effectiveness}")
            
            # Description
            desc = DeviationPolicy.get_deviation_description(deviation_type)
            print(f"  Description: {desc}")
        
        # Overall IRI
        print(f"\n{'='*70}")
        print(f"INCENTIVE ROBUSTNESS INDEX (IRI): {results['iri']:.3f}")
        print(f"  (Lower is better; 0.0 = perfect robustness)")
        
        if results['iri'] < 0.05:
            print(f"  ✓✓ Excellent: Protocol is highly robust against deviations")
        elif results['iri'] < 0.15:
            print(f"  ✓ Good: Protocol provides strong incentives for honesty")
        elif results['iri'] < 0.30:
            print(f"  ⚠ Moderate: Some deviations remain profitable")
        else:
            print(f"  ✗ Weak: Protocol needs improvement")
        
        print("="*70)
    
    def execute_sync(self) -> Dict[str, Any]:
        """Synchronous wrapper for execute."""
        return asyncio.run(self.execute())
    
    def save_results(self, results: Dict[str, Any], output_path: str):
        """Save deviation suite results to JSON file."""
        output_path = PathLib(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\nResults saved to: {output_path}")
