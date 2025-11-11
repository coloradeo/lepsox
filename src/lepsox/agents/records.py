"""
Record detection validators (State Record, County Record)
"""
from typing import Any, Dict
import pandas as pd

from .base import BaseValidator
from ..models.validation_result import ValidationResult


class StateRecordValidator(BaseValidator):
    """Agent 9: Validate State Record field (Column I)"""

    def __init__(self):
        super().__init__('State Record', use_ai=False)

    def validate(self, value: Any, row_data: Dict = None) -> ValidationResult:
        result = ValidationResult(self.field_name, value)

        # Optional field
        if pd.isna(value) or value == '':
            return result

        value_upper = str(value).upper().strip()

        if value_upper not in ['Y', 'N']:
            result.is_valid = False
            result.errors.append("State Record must be Y, N, or blank")

        result.correction = value_upper
        result.metadata['needs_inat_verification'] = True
        return result


class CountyRecordValidator(BaseValidator):
    """Agent 10: Validate County Record field (Column J)"""

    def __init__(self):
        super().__init__('County Record', use_ai=False)

    def validate(self, value: Any, row_data: Dict = None) -> ValidationResult:
        result = ValidationResult(self.field_name, value)

        # Optional field
        if pd.isna(value) or value == '':
            return result

        value_upper = str(value).upper().strip()

        if value_upper not in ['Y', 'N']:
            result.is_valid = False
            result.errors.append("County Record must be Y, N, or blank")

        result.correction = value_upper
        result.metadata['needs_inat_verification'] = True
        return result
