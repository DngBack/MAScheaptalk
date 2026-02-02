"""Reputation entity for agent credibility tracking."""
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime


@dataclass
class ReputationConfig:
    """Configuration for reputation system."""
    
    alpha: float = 0.1  # EMA learning rate
    floor: float = 0.2  # Minimum reputation (prevents complete death)
    ceiling: float = 1.0  # Maximum reputation
    threshold: float = 0.5  # Threshold for triggering verification
    slashing_penalty: float = 0.15  # Immediate penalty for caught lies
    redemption_bonus: float = 0.1  # Bonus for consistent good behavior
    redemption_threshold: float = 0.4  # Rep below this can earn redemption
    redemption_streak: int = 3  # Consecutive correct for redemption
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "alpha": self.alpha,
            "floor": self.floor,
            "ceiling": self.ceiling,
            "threshold": self.threshold,
            "slashing_penalty": self.slashing_penalty,
            "redemption_bonus": self.redemption_bonus,
            "redemption_threshold": self.redemption_threshold,
            "redemption_streak": self.redemption_streak
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ReputationConfig":
        """Create from dictionary."""
        return cls(
            alpha=data.get("alpha", 0.1),
            floor=data.get("floor", 0.2),
            ceiling=data.get("ceiling", 1.0),
            threshold=data.get("threshold", 0.5),
            slashing_penalty=data.get("slashing_penalty", 0.15),
            redemption_bonus=data.get("redemption_bonus", 0.1),
            redemption_threshold=data.get("redemption_threshold", 0.4),
            redemption_streak=data.get("redemption_streak", 3)
        )


@dataclass
class ReputationHistory:
    """Single reputation update record."""
    
    timestamp: datetime
    rep_before: float
    rep_after: float
    verification_result: bool
    slashed: bool
    redeemed: bool
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "rep_before": self.rep_before,
            "rep_after": self.rep_after,
            "verification_result": self.verification_result,
            "slashed": self.slashed,
            "redeemed": self.redeemed,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ReputationHistory":
        """Create from dictionary."""
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            rep_before=data["rep_before"],
            rep_after=data["rep_after"],
            verification_result=data["verification_result"],
            slashed=data["slashed"],
            redeemed=data["redeemed"],
            metadata=data.get("metadata", {})
        )


@dataclass
class Reputation:
    """
    Reputation entity for tracking agent credibility.
    
    Uses exponential moving average (EMA) for updates:
        rep_t+1 = (1 - α) * rep_t + α * verification_result
    
    Where:
        - α = learning rate (default 0.1)
        - rep ∈ [floor, ceiling] (default [0.2, 1.0])
        - verification_result = 1.0 if correct, 0.0 if wrong
    """
    
    agent_id: str
    rep_score: float = 0.7  # Initial reputation
    n_trials: int = 0
    n_pass: int = 0
    n_fail: int = 0
    consecutive_correct: int = 0
    consecutive_incorrect: int = 0
    history: List[ReputationHistory] = field(default_factory=list)
    config: ReputationConfig = field(default_factory=ReputationConfig)
    
    def update(
        self,
        verification_result: bool,
        evidence_quality: float = 1.0,
        force_slash: bool = False
    ) -> float:
        """
        Update reputation based on verification result.
        
        Args:
            verification_result: True if verification passed
            evidence_quality: Quality of evidence (0-1), affects update magnitude
            force_slash: Force immediate slashing penalty
            
        Returns:
            New reputation score
        """
        old_rep = self.rep_score
        
        # Update trial counts
        self.n_trials += 1
        if verification_result:
            self.n_pass += 1
            self.consecutive_correct += 1
            self.consecutive_incorrect = 0
        else:
            self.n_fail += 1
            self.consecutive_incorrect += 1
            self.consecutive_correct = 0
        
        # Determine if slashing should occur
        slashed = False
        if force_slash or (not verification_result and evidence_quality < 0.3):
            # Slash for caught lies or very poor evidence
            self.rep_score -= self.config.slashing_penalty
            slashed = True
        
        # Normal EMA update
        if not slashed:
            # Convert boolean to float for EMA
            result_value = 1.0 if verification_result else 0.0
            
            # Weight by evidence quality
            weighted_result = result_value * evidence_quality
            
            # EMA update: rep_t+1 = (1 - α) * rep_t + α * result
            self.rep_score = (1 - self.config.alpha) * self.rep_score + self.config.alpha * weighted_result
        
        # Check for redemption
        redeemed = False
        if (self.rep_score < self.config.redemption_threshold and
            self.consecutive_correct >= self.config.redemption_streak):
            # Grant redemption bonus
            self.rep_score += self.config.redemption_bonus
            redeemed = True
            # Reset streak after redemption
            self.consecutive_correct = 0
        
        # Apply floor and ceiling
        self.rep_score = max(self.config.floor, min(self.config.ceiling, self.rep_score))
        
        # Record history
        history_entry = ReputationHistory(
            timestamp=datetime.now(),
            rep_before=old_rep,
            rep_after=self.rep_score,
            verification_result=verification_result,
            slashed=slashed,
            redeemed=redeemed,
            metadata={
                "evidence_quality": evidence_quality,
                "consecutive_correct": self.consecutive_correct,
                "consecutive_incorrect": self.consecutive_incorrect
            }
        )
        self.history.append(history_entry)
        
        return self.rep_score
    
    def should_trigger_verification(self) -> bool:
        """
        Check if reputation is low enough to trigger automatic verification.
        
        Returns:
            True if rep < threshold
        """
        return self.rep_score < self.config.threshold
    
    def get_claim_cost_multiplier(self) -> float:
        """
        Get cost multiplier for making strong claims.
        
        Lower reputation = higher cost for claiming.
        
        Returns:
            Cost multiplier (>= 1.0)
        """
        # cost_multiplier = 1 / rep
        # So low rep (e.g., 0.3) -> 3.33x cost
        # High rep (e.g., 0.9) -> 1.11x cost
        return 1.0 / max(self.rep_score, self.config.floor)
    
    def get_decision_weight(self) -> float:
        """
        Get weight for this agent's contribution to final decision.
        
        Returns:
            Weight proportional to reputation (0-1)
        """
        return self.rep_score
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get reputation statistics.
        
        Returns:
            Dictionary with stats
        """
        pass_rate = self.n_pass / self.n_trials if self.n_trials > 0 else 0.0
        
        return {
            "agent_id": self.agent_id,
            "rep_score": self.rep_score,
            "n_trials": self.n_trials,
            "n_pass": self.n_pass,
            "n_fail": self.n_fail,
            "pass_rate": pass_rate,
            "consecutive_correct": self.consecutive_correct,
            "consecutive_incorrect": self.consecutive_incorrect,
            "below_threshold": self.should_trigger_verification(),
            "claim_cost_multiplier": self.get_claim_cost_multiplier(),
            "decision_weight": self.get_decision_weight()
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "agent_id": self.agent_id,
            "rep_score": self.rep_score,
            "n_trials": self.n_trials,
            "n_pass": self.n_pass,
            "n_fail": self.n_fail,
            "consecutive_correct": self.consecutive_correct,
            "consecutive_incorrect": self.consecutive_incorrect,
            "history": [h.to_dict() for h in self.history],
            "config": self.config.to_dict()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Reputation":
        """Create Reputation from dictionary."""
        return cls(
            agent_id=data["agent_id"],
            rep_score=data["rep_score"],
            n_trials=data["n_trials"],
            n_pass=data["n_pass"],
            n_fail=data["n_fail"],
            consecutive_correct=data.get("consecutive_correct", 0),
            consecutive_incorrect=data.get("consecutive_incorrect", 0),
            history=[ReputationHistory.from_dict(h) for h in data.get("history", [])],
            config=ReputationConfig.from_dict(data.get("config", {}))
        )
