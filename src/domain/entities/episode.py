"""Episode entity."""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from .task import Task
from .message import Message


@dataclass
class VerificationResult:
    """Result from verifying an episode."""
    
    label_correct: bool
    evidence_provided: bool
    evidence_match_score: float  # 0-1
    predicted_label: Optional[str] = None
    additional_info: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "label_correct": self.label_correct,
            "evidence_provided": self.evidence_provided,
            "evidence_match_score": self.evidence_match_score,
            "predicted_label": self.predicted_label,
            "additional_info": self.additional_info
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VerificationResult":
        """Create VerificationResult from dictionary."""
        return cls(
            label_correct=data["label_correct"],
            evidence_provided=data["evidence_provided"],
            evidence_match_score=data["evidence_match_score"],
            predicted_label=data.get("predicted_label"),
            additional_info=data.get("additional_info", {})
        )


@dataclass
class Episode:
    """Represents one run of a task with a specific protocol and deviation type."""
    
    episode_id: str
    task: Task
    protocol_id: str
    deviation_type: str  # "honest", "no_evidence", "lie", "withhold", etc.
    transcript: List[Message] = field(default_factory=list)
    verifier_result: Optional[VerificationResult] = None
    metrics: Dict[str, float] = field(default_factory=dict)
    payoff: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "episode_id": self.episode_id,
            "task": self.task.to_dict(),
            "protocol_id": self.protocol_id,
            "deviation_type": self.deviation_type,
            "transcript": [m.to_dict() for m in self.transcript],
            "verifier_result": self.verifier_result.to_dict() if self.verifier_result else None,
            "metrics": self.metrics,
            "payoff": self.payoff
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Episode":
        """Create Episode from dictionary."""
        return cls(
            episode_id=data["episode_id"],
            task=Task.from_dict(data["task"]),
            protocol_id=data["protocol_id"],
            deviation_type=data["deviation_type"],
            transcript=[Message.from_dict(m) for m in data.get("transcript", [])],
            verifier_result=VerificationResult.from_dict(data["verifier_result"]) if data.get("verifier_result") else None,
            metrics=data.get("metrics", {}),
            payoff=data.get("payoff", 0.0)
        )
