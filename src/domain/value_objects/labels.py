"""FEVER label value object."""
from enum import Enum


class FEVERLabel(str, Enum):
    """Labels for FEVER dataset claims."""
    
    SUPPORTS = "SUPPORTS"
    REFUTES = "REFUTES"
    NOT_ENOUGH_INFO = "NOT ENOUGH INFO"
    
    def __str__(self) -> str:
        return self.value
    
    @classmethod
    def from_string(cls, label_str: str) -> "FEVERLabel":
        """Create FEVERLabel from string, handling variations."""
        label_upper = label_str.upper()
        
        # Handle common variations
        if label_upper in ["SUPPORTS", "SUPPORTED"]:
            return cls.SUPPORTS
        elif label_upper in ["REFUTES", "REFUTED"]:
            return cls.REFUTES
        elif label_upper in ["NOT ENOUGH INFO", "NEI", "NOT_ENOUGH_INFO"]:
            return cls.NOT_ENOUGH_INFO
        else:
            raise ValueError(f"Unknown FEVER label: {label_str}")
