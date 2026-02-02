"""Base protocol abstract class."""
from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseProtocol(ABC):
    """Abstract base class for communication protocols."""
    
    @abstractmethod
    def get_sender_system_prompt(self, deviation_type: str = "honest") -> str:
        """
        Get system prompt for Sender agent.
        
        Args:
            deviation_type: Type of deviation ("honest", "no_evidence", "lie", etc.)
            
        Returns:
            System prompt string
        """
        pass
    
    @abstractmethod
    def get_receiver_system_prompt(self) -> str:
        """
        Get system prompt for Receiver agent.
        
        Returns:
            System prompt string
        """
        pass
    
    @abstractmethod
    def get_protocol_id(self) -> str:
        """Return unique protocol identifier."""
        pass
    
    @abstractmethod
    def get_config(self) -> Dict[str, Any]:
        """Return protocol configuration."""
        pass
