"""Verifier interface."""
from abc import ABC, abstractmethod
from ..entities.episode import Episode, VerificationResult


class Verifier(ABC):
    """Abstract interface for verifiers that check episode correctness."""
    
    @abstractmethod
    def verify(self, episode: Episode) -> VerificationResult:
        """
        Verify an episode against ground truth.
        
        Args:
            episode: Episode to verify
            
        Returns:
            VerificationResult with correctness metrics
        """
        pass
