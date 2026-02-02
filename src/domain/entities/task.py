"""Task entity."""
from dataclasses import dataclass
from typing import List, Dict, Any
from ..value_objects.labels import FEVERLabel
from .evidence import Evidence


@dataclass
class Task:
    """Represents a task from the FEVER dataset (or other benchmarks)."""
    
    task_id: str
    claim: str
    label: FEVERLabel
    evidence: List[Evidence]
    metadata: Dict[str, Any]
    
    def __post_init__(self):
        if not isinstance(self.label, FEVERLabel):
            self.label = FEVERLabel.from_string(str(self.label))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "task_id": self.task_id,
            "claim": self.claim,
            "label": str(self.label),
            "evidence": [e.to_dict() for e in self.evidence],
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        """Create Task from dictionary."""
        return cls(
            task_id=data["task_id"],
            claim=data["claim"],
            label=FEVERLabel.from_string(data["label"]),
            evidence=[Evidence.from_dict(e) for e in data["evidence"]],
            metadata=data.get("metadata", {})
        )
