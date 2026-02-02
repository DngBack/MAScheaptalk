"""Storage interface."""
from abc import ABC, abstractmethod
from typing import List, Optional
from ..entities.episode import Episode


class Storage(ABC):
    """Abstract interface for storing and retrieving episodes."""
    
    @abstractmethod
    def save_episode(self, episode: Episode) -> None:
        """
        Save an episode.
        
        Args:
            episode: Episode to save
        """
        pass
    
    @abstractmethod
    def load_episodes(self, limit: Optional[int] = None) -> List[Episode]:
        """
        Load episodes from storage.
        
        Args:
            limit: Maximum number of episodes to load (None for all)
            
        Returns:
            List of Episode objects
        """
        pass
    
    @abstractmethod
    def clear(self) -> None:
        """Clear all stored episodes."""
        pass
