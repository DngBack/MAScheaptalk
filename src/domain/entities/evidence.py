"""Evidence entity."""
from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class Evidence:
    """Represents a piece of evidence (e.g., Wikipedia sentence, document excerpt)."""
    
    evidence_id: str
    text: str
    source: Optional[str] = None  # e.g., Wikipedia page title
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "evidence_id": self.evidence_id,
            "text": self.text,
            "source": self.source,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Evidence":
        """Create Evidence from dictionary."""
        return cls(
            evidence_id=data["evidence_id"],
            text=data["text"],
            source=data.get("source"),
            metadata=data.get("metadata", {})
        )
