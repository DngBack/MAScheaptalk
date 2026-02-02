"""FEVER scoring utilities."""
from typing import List, Dict, Any

import sys
from pathlib import Path
src_path = Path(__file__).parent.parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from domain.entities.episode import Episode


class FEVERScoring:
    """Scoring utilities for FEVER episodes."""
    
    @staticmethod
    def compute_metrics(episodes: List[Episode]) -> Dict[str, float]:
        """
        Compute aggregate metrics across multiple episodes.
        
        Args:
            episodes: List of episodes to compute metrics for
            
        Returns:
            Dictionary of metrics
        """
        if not episodes:
            return {}
        
        # Collect metrics
        label_correct_count = 0
        evidence_provided_count = 0
        evidence_match_scores = []
        total_cost = 0
        payoffs = []
        
        for episode in episodes:
            if episode.verifier_result:
                if episode.verifier_result.label_correct:
                    label_correct_count += 1
                if episode.verifier_result.evidence_provided:
                    evidence_provided_count += 1
                evidence_match_scores.append(episode.verifier_result.evidence_match_score)
            
            # Collect cost from metrics
            if "total_cost" in episode.metrics:
                total_cost += episode.metrics["total_cost"]
            
            payoffs.append(episode.payoff)
        
        # Compute aggregates
        n = len(episodes)
        
        metrics = {
            "accuracy": label_correct_count / n,
            "evidence_compliance": evidence_provided_count / n,
            "evidence_match_score": sum(evidence_match_scores) / n if evidence_match_scores else 0.0,
            "mean_payoff": sum(payoffs) / n if payoffs else 0.0,
            "total_cost": total_cost,
            "mean_cost": total_cost / n if n > 0 else 0.0,
            "num_episodes": n
        }
        
        return metrics
    
    @staticmethod
    def compute_deviation_gain(
        honest_episodes: List[Episode],
        deviation_episodes: List[Episode]
    ) -> Dict[str, Any]:
        """
        Compute Deviation Gain (DG) between honest and deviation episodes.
        
        DG = mean(payoff_deviation) - mean(payoff_honest)
        
        Args:
            honest_episodes: Episodes with honest strategy
            deviation_episodes: Episodes with deviation strategy
            
        Returns:
            Dictionary with DG metrics
        """
        honest_metrics = FEVERScoring.compute_metrics(honest_episodes)
        deviation_metrics = FEVERScoring.compute_metrics(deviation_episodes)
        
        dg = deviation_metrics.get("mean_payoff", 0.0) - honest_metrics.get("mean_payoff", 0.0)
        
        # Count how many deviations had positive gain
        positive_dg_count = sum(
            1 for h_ep, d_ep in zip(honest_episodes, deviation_episodes)
            if d_ep.payoff > h_ep.payoff
        )
        
        percent_positive = (positive_dg_count / len(honest_episodes) * 100) if honest_episodes else 0.0
        
        return {
            "deviation_gain": dg,
            "percent_dg_positive": percent_positive,
            "honest_mean_payoff": honest_metrics.get("mean_payoff", 0.0),
            "deviation_mean_payoff": deviation_metrics.get("mean_payoff", 0.0),
            "honest_accuracy": honest_metrics.get("accuracy", 0.0),
            "deviation_accuracy": deviation_metrics.get("accuracy", 0.0),
            "honest_evidence_compliance": honest_metrics.get("evidence_compliance", 0.0),
            "deviation_evidence_compliance": deviation_metrics.get("evidence_compliance", 0.0)
        }
