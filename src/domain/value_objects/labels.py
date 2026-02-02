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
        """Create FEVERLabel from string or int, handling variations."""
        # HuggingFace FEVER sometimes uses int labels: 0=SUPPORTS, 1=REFUTES, 2=NOT ENOUGH INFO
        if isinstance(label_str, int):
            label_map = {0: cls.SUPPORTS, 1: cls.REFUTES, 2: cls.NOT_ENOUGH_INFO}
            if label_str in label_map:
                return label_map[label_str]
            label_str = str(label_str)
        label_upper = str(label_str).strip().upper()
        # Numeric string from HF
        if label_upper == "0":
            return cls.SUPPORTS
        if label_upper == "1":
            return cls.REFUTES
        if label_upper == "2":
            return cls.NOT_ENOUGH_INFO
        # Handle common variations
        if label_upper in ["SUPPORTS", "SUPPORTED"]:
            return cls.SUPPORTS
        elif label_upper in ["REFUTES", "REFUTED"]:
            return cls.REFUTES
        elif label_upper in ["NOT ENOUGH INFO", "NEI", "NOT_ENOUGH_INFO"]:
            return cls.NOT_ENOUGH_INFO
        else:
            raise ValueError(f"Unknown FEVER label: {label_str}")
