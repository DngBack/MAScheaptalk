"""Message entity."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from ..value_objects.role import AgentRole
from .evidence import Evidence


@dataclass
class Message:
    """Represents a message in the conversation between agents."""
    
    role: AgentRole
    content: str
    evidence: Optional[List[Evidence]] = None
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not isinstance(self.role, AgentRole):
            self.role = AgentRole(self.role)
        if self.evidence is None:
            self.evidence = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "role": str(self.role),
            "content": self.content,
            "evidence": [e.to_dict() for e in self.evidence] if self.evidence else [],
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """Create Message from dictionary."""
        return cls(
            role=AgentRole(data["role"]),
            content=data["content"],
            evidence=[Evidence.from_dict(e) for e in data.get("evidence", [])],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metadata=data.get("metadata", {})
        )
