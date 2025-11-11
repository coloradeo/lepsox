"""
Validation result data model
"""
from typing import Any, Dict, List, Optional


class ValidationResult:
    """Container for validation results of a single field"""

    def __init__(self, field_name: str, value: Any):
        self.field_name = field_name
        self.value = value
        self.is_valid = True
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.correction: Optional[Any] = None
        self.metadata: Dict[str, Any] = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            'field': self.field_name,
            'value': self.value,
            'is_valid': self.is_valid,
            'errors': self.errors,
            'warnings': self.warnings,
            'correction': self.correction,
            'metadata': self.metadata
        }

    def __repr__(self) -> str:
        status = "✓" if self.is_valid else "✗"
        return f"<ValidationResult {status} {self.field_name}={self.value}>"
