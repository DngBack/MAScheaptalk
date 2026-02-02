"""Agent role value object."""
from enum import Enum


class AgentRole(str, Enum):
    """Roles that agents can have in the multi-agent system."""
    
    SENDER = "sender"
    RECEIVER = "receiver"
    VERIFIER = "verifier"
    
    def __str__(self) -> str:
        return self.value
