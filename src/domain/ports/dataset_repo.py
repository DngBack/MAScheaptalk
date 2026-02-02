"""Dataset Repository interface."""
from abc import ABC, abstractmethod
from typing import Iterator, Optional
from ..entities.task import Task


class DatasetRepository(ABC):
    """Abstract interface for dataset repositories."""
    
    @abstractmethod
    def get_task(self, idx: int) -> Task:
        """
        Get a specific task by index.
        
        Args:
            idx: Index of the task
            
        Returns:
            Task object
        """
        pass
    
    @abstractmethod
    def iter_tasks(self, limit: Optional[int] = None) -> Iterator[Task]:
        """
        Iterate over tasks.
        
        Args:
            limit: Maximum number of tasks to return (None for all)
            
        Yields:
            Task objects
        """
        pass
    
    @abstractmethod
    def get_num_tasks(self) -> int:
        """Return total number of tasks in the repository."""
        pass
