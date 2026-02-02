"""Deviation metrics for game-theoretic analysis."""
from typing import List, Dict, Any, Optional
import numpy as np
from dataclasses import dataclass

import sys
from pathlib import Path
src_path = Path(__file__).parent.parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from domain.entities.episode import Episode


@dataclass
class DeviationGainStats:
    """Statistics for deviation gain analysis."""
    
    deviation_type: str
    deviation_gain: float
    percent_dg_positive: float
    honest_mean: float
    deviation_mean: float
    honest_std: float
    deviation_std: float
    count: int
    confidence_interval_95: Optional[tuple[float, float]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "deviation_type": self.deviation_type,
            "deviation_gain": self.deviation_gain,
            "percent_dg_positive": self.percent_dg_positive,
            "honest_mean": self.honest_mean,
            "deviation_mean": self.deviation_mean,
            "honest_std": self.honest_std,
            "deviation_std": self.deviation_std,
            "count": self.count,
            "confidence_interval_95": self.confidence_interval_95
        }
    
    def is_effective(self) -> bool:
        """Check if protocol is effective against this deviation."""
        return self.deviation_gain < 0
    
    def effectiveness_level(self) -> str:
        """Get effectiveness level description."""
        if self.deviation_gain < -0.3:
            return "very_effective"
        elif self.deviation_gain < 0:
            return "effective"
        elif self.deviation_gain < 0.1:
            return "weak"
        else:
            return "ineffective"


class DeviationMetrics:
    """
    Comprehensive metrics for deviation analysis.
    
    Provides statistical analysis of deviation gain, including:
    - Mean DG and variance
    - Confidence intervals
    - Breakdown by task difficulty
    - Incentive Robustness Index (IRI)
    """
    
    @staticmethod
    def compute_deviation_gain(
        honest_episodes: List[Episode],
        deviation_episodes: List[Episode],
        deviation_type: str
    ) -> DeviationGainStats:
        """
        Compute comprehensive deviation gain statistics.
        
        Args:
            honest_episodes: Episodes with honest behavior
            deviation_episodes: Episodes with deviation behavior
            deviation_type: Type of deviation
            
        Returns:
            DeviationGainStats object with full analysis
        """
        if not honest_episodes or not deviation_episodes:
            return DeviationGainStats(
                deviation_type=deviation_type,
                deviation_gain=0.0,
                percent_dg_positive=0.0,
                honest_mean=0.0,
                deviation_mean=0.0,
                honest_std=0.0,
                deviation_std=0.0,
                count=0
            )
        
        # Extract payoffs
        honest_payoffs = np.array([ep.payoff for ep in honest_episodes])
        deviation_payoffs = np.array([ep.payoff for ep in deviation_episodes])
        
        # Align to same length
        min_len = min(len(honest_payoffs), len(deviation_payoffs))
        honest_payoffs = honest_payoffs[:min_len]
        deviation_payoffs = deviation_payoffs[:min_len]
        
        # Mean payoffs
        honest_mean = float(np.mean(honest_payoffs))
        deviation_mean = float(np.mean(deviation_payoffs))
        
        # Standard deviations
        honest_std = float(np.std(honest_payoffs))
        deviation_std = float(np.std(deviation_payoffs))
        
        # Deviation gain
        dg = deviation_mean - honest_mean
        
        # Per-episode DG
        per_episode_dg = deviation_payoffs - honest_payoffs
        
        # Percent positive DG
        percent_positive = float((np.sum(per_episode_dg > 0) / len(per_episode_dg)) * 100)
        
        # 95% confidence interval for DG
        # Using paired t-test approach
        se_dg = np.std(per_episode_dg) / np.sqrt(len(per_episode_dg))
        ci_margin = 1.96 * se_dg  # 95% CI
        ci_lower = dg - ci_margin
        ci_upper = dg + ci_margin
        
        return DeviationGainStats(
            deviation_type=deviation_type,
            deviation_gain=float(dg),
            percent_dg_positive=percent_positive,
            honest_mean=honest_mean,
            deviation_mean=deviation_mean,
            honest_std=honest_std,
            deviation_std=deviation_std,
            count=min_len,
            confidence_interval_95=(float(ci_lower), float(ci_upper))
        )
    
    @staticmethod
    def compute_iri(dg_stats: List[DeviationGainStats]) -> float:
        """
        Compute Incentive Robustness Index (IRI).
        
        IRI = mean(max(DG, 0)) across all deviation types
        
        Lower IRI is better:
        - IRI = 0: No deviation is profitable (perfect)
        - IRI < 0.1: Very robust
        - IRI < 0.3: Moderately robust
        - IRI >= 0.3: Weak robustness
        
        Args:
            dg_stats: List of DeviationGainStats
            
        Returns:
            IRI score
        """
        if not dg_stats:
            return 0.0
        
        # Only count positive DG (profitable deviations)
        positive_dgs = [max(stat.deviation_gain, 0.0) for stat in dg_stats]
        
        return float(np.mean(positive_dgs))
    
    @staticmethod
    def breakdown_by_difficulty(
        honest_episodes: List[Episode],
        deviation_episodes: List[Episode],
        deviation_type: str
    ) -> Dict[str, DeviationGainStats]:
        """
        Break down deviation gain by task difficulty.
        
        Difficulty is inferred from honest performance:
        - Easy: honest accuracy > 0.8
        - Medium: 0.4 <= honest accuracy <= 0.8
        - Hard: honest accuracy < 0.4
        
        Args:
            honest_episodes: Episodes with honest behavior
            deviation_episodes: Episodes with deviation behavior
            deviation_type: Type of deviation
            
        Returns:
            Dictionary mapping difficulty level to DG stats
        """
        # Group episodes by difficulty
        easy_honest = []
        easy_deviation = []
        medium_honest = []
        medium_deviation = []
        hard_honest = []
        hard_deviation = []
        
        for i, h_ep in enumerate(honest_episodes):
            if i >= len(deviation_episodes):
                break
            
            d_ep = deviation_episodes[i]
            
            # Simple difficulty heuristic based on honest performance
            if h_ep.verifier_result.label_correct and h_ep.verifier_result.evidence_match_score > 0.8:
                easy_honest.append(h_ep)
                easy_deviation.append(d_ep)
            elif h_ep.verifier_result.label_correct or h_ep.verifier_result.evidence_match_score > 0.4:
                medium_honest.append(h_ep)
                medium_deviation.append(d_ep)
            else:
                hard_honest.append(h_ep)
                hard_deviation.append(d_ep)
        
        # Compute DG for each difficulty level
        breakdown = {}
        
        if easy_honest:
            breakdown["easy"] = DeviationMetrics.compute_deviation_gain(
                easy_honest, easy_deviation, f"{deviation_type}_easy"
            )
        
        if medium_honest:
            breakdown["medium"] = DeviationMetrics.compute_deviation_gain(
                medium_honest, medium_deviation, f"{deviation_type}_medium"
            )
        
        if hard_honest:
            breakdown["hard"] = DeviationMetrics.compute_deviation_gain(
                hard_honest, hard_deviation, f"{deviation_type}_hard"
            )
        
        return breakdown
    
    @staticmethod
    def generate_comparison_table(
        dg_stats_list: List[DeviationGainStats],
        include_ci: bool = True
    ) -> str:
        """
        Generate formatted comparison table for deviation gains.
        
        Args:
            dg_stats_list: List of DeviationGainStats
            include_ci: Whether to include confidence intervals
            
        Returns:
            Formatted table string
        """
        if not dg_stats_list:
            return "No deviation statistics available."
        
        # Header
        lines = []
        lines.append("="*80)
        lines.append("DEVIATION GAIN COMPARISON")
        lines.append("="*80)
        
        if include_ci:
            lines.append(f"{'Deviation':<20} {'DG':>8} {'95% CI':>20} {'%DG>0':>8} {'Status':<15}")
        else:
            lines.append(f"{'Deviation':<20} {'DG':>8} {'%DG>0':>8} {'Status':<15}")
        
        lines.append("-"*80)
        
        # Sort by DG (most negative first = most effective)
        sorted_stats = sorted(dg_stats_list, key=lambda x: x.deviation_gain)
        
        for stat in sorted_stats:
            if stat.deviation_type == "honest":
                continue  # Skip honest baseline in comparison
            
            # Format DG with sign
            dg_str = f"{stat.deviation_gain:+.3f}"
            
            # Format confidence interval
            if include_ci and stat.confidence_interval_95:
                ci_lower, ci_upper = stat.confidence_interval_95
                ci_str = f"[{ci_lower:+.3f}, {ci_upper:+.3f}]"
            else:
                ci_str = ""
            
            # Format percent
            pct_str = f"{stat.percent_dg_positive:.1f}%"
            
            # Status
            effectiveness = stat.effectiveness_level()
            status_symbols = {
                "very_effective": "✓✓ Very effective",
                "effective": "✓ Effective",
                "weak": "⚠ Weak",
                "ineffective": "✗ Ineffective"
            }
            status = status_symbols.get(effectiveness, "Unknown")
            
            if include_ci:
                lines.append(
                    f"{stat.deviation_type:<20} {dg_str:>8} {ci_str:>20} {pct_str:>8} {status:<15}"
                )
            else:
                lines.append(
                    f"{stat.deviation_type:<20} {dg_str:>8} {pct_str:>8} {status:<15}"
                )
        
        lines.append("="*80)
        
        return "\n".join(lines)
    
    @staticmethod
    def generate_summary_report(
        all_dg_stats: Dict[str, DeviationGainStats],
        iri: float
    ) -> str:
        """
        Generate comprehensive summary report.
        
        Args:
            all_dg_stats: Dictionary mapping deviation_type to stats
            iri: Incentive Robustness Index
            
        Returns:
            Formatted report string
        """
        lines = []
        lines.append("\n" + "="*80)
        lines.append("COMPREHENSIVE DEVIATION ANALYSIS REPORT")
        lines.append("="*80)
        
        # Overall statistics
        lines.append("\nOVERALL PROTOCOL ROBUSTNESS:")
        lines.append(f"  Incentive Robustness Index (IRI): {iri:.3f}")
        
        if iri < 0.05:
            lines.append("  Rating: ✓✓ EXCELLENT - Highly robust against deviations")
        elif iri < 0.15:
            lines.append("  Rating: ✓ GOOD - Strong incentives for honesty")
        elif iri < 0.30:
            lines.append("  Rating: ⚠ MODERATE - Some deviations remain profitable")
        else:
            lines.append("  Rating: ✗ WEAK - Protocol needs improvement")
        
        # Count effective vs ineffective
        effective_count = sum(1 for stat in all_dg_stats.values() 
                            if stat.deviation_type != "honest" and stat.is_effective())
        total_deviations = len([k for k in all_dg_stats.keys() if k != "honest"])
        
        lines.append(f"\n  Deviations discouraged: {effective_count}/{total_deviations}")
        
        # Per-deviation summary
        lines.append("\nPER-DEVIATION SUMMARY:")
        
        for dev_type, stat in sorted(all_dg_stats.items(), key=lambda x: x[1].deviation_gain):
            if dev_type == "honest":
                continue
            
            lines.append(f"\n  {dev_type.upper()}:")
            lines.append(f"    Deviation Gain:  {stat.deviation_gain:+.3f}")
            lines.append(f"    % Profitable:    {stat.percent_dg_positive:.1f}%")
            lines.append(f"    Effectiveness:   {stat.effectiveness_level()}")
            
            if stat.confidence_interval_95:
                ci_lower, ci_upper = stat.confidence_interval_95
                lines.append(f"    95% CI:          [{ci_lower:+.3f}, {ci_upper:+.3f}]")
        
        lines.append("\n" + "="*80)
        
        return "\n".join(lines)
