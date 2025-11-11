"""
Metadata field validators (Location, Name, Comments)
"""
from typing import Any, Dict
import pandas as pd
import re

from .base import BaseValidator
from ..models.validation_result import ValidationResult


class LocationValidator(BaseValidator):
    """Agent 11: Validate Specific Location field (Column K)"""

    def __init__(self, llm):
        super().__init__('Specific Location', llm)

    def validate(self, value: Any, row_data: Dict = None) -> ValidationResult:
        result = ValidationResult(self.field_name, value)

        if pd.isna(value) or value == '':
            result.is_valid = False
            result.errors.append("Specific Location is required")
            return result

        location = str(value).strip()

        if len(location) > 50:
            result.is_valid = False
            result.errors.append(f"Location exceeds 50 characters: {len(location)}")
            result.metadata['overflow_to_comments'] = location[50:]

        return result


class NameValidator(BaseValidator):
    """Agent 14: Validate Name field (Column N)"""

    def __init__(self, llm):
        super().__init__('Name', llm)

    def validate(self, value: Any, row_data: Dict = None) -> ValidationResult:
        result = ValidationResult(self.field_name, value)

        # Optional field
        if pd.isna(value) or value == '':
            return result

        name_code = str(value).strip()

        if len(name_code) > 3:
            result.is_valid = False
            result.errors.append(f"Name code must be 3 characters or less")

        # TODO: Check against contributor codes master file
        result.metadata['needs_contributor_check'] = True

        return result


class CommentValidator(BaseValidator):
    """Agent 15: Validate Comments field (Column O)"""

    def __init__(self, llm):
        super().__init__('Comments', llm)

    def validate(self, value: Any, row_data: Dict = None) -> ValidationResult:
        result = ValidationResult(self.field_name, value)

        # Optional field
        if pd.isna(value) or value == '':
            return result

        comments = str(value).strip()

        if len(comments) > 120:
            result.is_valid = False
            result.errors.append(f"Comments exceed 120 characters: {len(comments)}")

        # Check for GPS coordinates pattern
        gps_pattern = r'[-+]?\d+\.?\d*,\s*[-+]?\d+\.?\d*'
        if re.search(gps_pattern, comments):
            result.metadata['has_gps_coords'] = True

        return result
