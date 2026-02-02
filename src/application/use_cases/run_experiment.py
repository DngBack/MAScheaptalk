"""Run experiment use case."""
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
from domain.ports.dataset_repo import DatasetRepository
from domain.ports.storage import Storage
from application.use_cases.run_episode import RunEpisode
from application.scoring.fever_scoring import FEVERScoring


class RunExperiment:
    """Use case for running a full experiment with multiple episodes."""
    
    def __init__(
        self,
        run_episode: RunEpisode,
        dataset_repo: DatasetRepository,
        storage: Storage,
        num_tasks: int = 100,
        deviation_types: Optional[List[str]] = None
    ):
        """
        Initialize run experiment use case.
        
        Args:
            run_episode: RunEpisode use case instance
            dataset_repo: Dataset repository
            storage: Storage for episodes
            num_tasks: Number of tasks to run
            deviation_types: List of deviation types to test
        """
        self.run_episode = run_episode
        self.dataset_repo = dataset_repo
        self.storage = storage
        self.num_tasks = num_tasks
        self.deviation_types = deviation_types or ["honest", "no_evidence"]
    
    async def execute(self) -> Dict[str, Any]:
        """
        Execute the experiment.
        
        Returns:
            Dictionary with experiment results and metrics
        """
        print(f"Starting experiment with {self.num_tasks} tasks")
        print(f"Deviation types: {self.deviation_types}")
        
        # Collect episodes by deviation type
        episodes_by_type: Dict[str, List[Episode]] = {dt: [] for dt in self.deviation_types}
        
        # Iterate through tasks
        task_count = 0
        for task in self.dataset_repo.iter_tasks(limit=self.num_tasks):
            task_count += 1
            print(f"\nProcessing task {task_count}/{self.num_tasks}: {task.task_id}")
            
            # Run episode for each deviation type
            for deviation_type in self.deviation_types:
                print(f"  Running with deviation_type={deviation_type}")
                
                try:
                    episode = await self.run_episode.execute(task, deviation_type)
                    
                    # Store episode
                    self.storage.save_episode(episode)
                    episodes_by_type[deviation_type].append(episode)
                    
                    # Print quick summary
                    print(f"    Label correct: {episode.verifier_result.label_correct}")
                    print(f"    Evidence provided: {episode.verifier_result.evidence_provided}")
                    print(f"    Payoff: {episode.payoff:.3f}")
                
                except Exception as e:
                    print(f"    Error: {e}")
                    continue
        
        # Compute metrics
        print("\n" + "="*60)
        print("EXPERIMENT RESULTS")
        print("="*60)
        
        results = {
            "num_tasks": task_count,
            "deviation_types": self.deviation_types,
            "metrics_by_type": {}
        }
        
        # Metrics for each deviation type
        for deviation_type, episodes in episodes_by_type.items():
            if episodes:
                metrics = FEVERScoring.compute_metrics(episodes)
                results["metrics_by_type"][deviation_type] = metrics
                
                print(f"\n{deviation_type.upper()}:")
                print(f"  Accuracy: {metrics['accuracy']:.3f}")
                print(f"  Evidence compliance: {metrics['evidence_compliance']:.3f}")
                print(f"  Evidence match: {metrics['evidence_match_score']:.3f}")
                print(f"  Mean payoff: {metrics['mean_payoff']:.3f}")
                print(f"  Mean cost: {metrics['mean_cost']:.6f}")
        
        # Compute deviation gain if we have honest and deviation
        if "honest" in episodes_by_type and any(dt != "honest" for dt in self.deviation_types):
            print("\nDEVIATION GAIN ANALYSIS:")
            
            for deviation_type in self.deviation_types:
                if deviation_type != "honest" and deviation_type in episodes_by_type:
                    dg_metrics = FEVERScoring.compute_deviation_gain(
                        episodes_by_type["honest"],
                        episodes_by_type[deviation_type]
                    )
                    
                    results[f"dg_{deviation_type}"] = dg_metrics
                    
                    print(f"\n  {deviation_type} vs honest:")
                    print(f"    Deviation Gain: {dg_metrics['deviation_gain']:.3f}")
                    print(f"    % episodes with DG > 0: {dg_metrics['percent_dg_positive']:.1f}%")
                    
                    if dg_metrics['deviation_gain'] < 0:
                        print(f"    ✓ Protocol is effective! Deviation is disadvantageous.")
                    else:
                        print(f"    ✗ Warning: Deviation is advantageous. Protocol may need improvement.")
        
        print("\n" + "="*60)
        
        return results
    
    def execute_sync(self) -> Dict[str, Any]:
        """Synchronous wrapper for execute."""
        return asyncio.run(self.execute())
    
    def save_summary(self, results: Dict[str, Any], output_path: str):
        """Save experiment summary to JSON file."""
        output_path = PathLib(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\nSummary saved to: {output_path}")
