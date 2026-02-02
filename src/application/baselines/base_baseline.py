"""Base class for baseline methods."""
from abc import ABC, abstractmethod
from typing import Dict, Any

import sys
from pathlib import Path
src_path = Path(__file__).parent.parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from domain.entities.task import Task
from domain.entities.episode import Episode
from domain.ports.llm_client import LLMClient


class BaseBaseline(ABC):
    """
    Abstract base class for baseline methods.
    
    All baseline methods must implement this interface for fair comparison.
    """
    
    def __init__(self, llm_client: LLMClient, **kwargs):
        """
        Initialize baseline method.
        
        Args:
            llm_client: LLM client for making predictions
            **kwargs: Additional configuration parameters
        """
        self.llm_client = llm_client
        self.config = kwargs
    
    @abstractmethod
    async def execute(self, task: Task) -> Episode:
        """
        Execute baseline method on a task.
        
        Args:
            task: Task to solve
            
        Returns:
            Episode with results
        """
        pass
    
    def execute_sync(self, task: Task) -> Episode:
        """Synchronous wrapper for execute."""
        import asyncio
        return asyncio.run(self.execute(task))
    
    @abstractmethod
    def get_baseline_id(self) -> str:
        """
        Get unique identifier for this baseline.
        
        Returns:
            Baseline identifier string
        """
        pass
    
    def get_config(self) -> Dict[str, Any]:
        """
        Get baseline configuration.
        
        Returns:
            Configuration dictionary
        """
        return {
            "baseline_id": self.get_baseline_id(),
            **self.config
        }
    
    def get_system_prompt(self) -> str:
        """
        Get system prompt for this baseline.
        
        Can be overridden by subclasses.
        
        Returns:
            System prompt string
        """
        return """You are an AI assistant helping to verify factual claims.

Your task is to analyze the given FEVER claim and determine if it is:
- SUPPORTS: The claim is supported by evidence
- REFUTES: The claim is refuted by evidence  
- NOT ENOUGH INFO: There is not enough information to determine

Please provide your assessment and reasoning."""
    
    def _create_user_prompt(self, task: Task) -> str:
        """
        Create user prompt from task.
        
        Args:
            task: Task to create prompt for
            
        Returns:
            User prompt string
        """
        return f"""Please analyze the following claim:

Claim: {task.claim}

Determine if this claim is SUPPORTS, REFUTES, or NOT ENOUGH INFO.

Provide your answer in this format:
Assessment: [SUPPORTS/REFUTES/NOT ENOUGH INFO]
Reasoning: [Your reasoning here]"""
