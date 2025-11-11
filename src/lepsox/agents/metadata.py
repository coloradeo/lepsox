"""
Metadata field validators (Location, Name, Comments)
"""
from typing import Any, Dict
import pandas as pd
import re

from .base import BaseValidator
from ..models.validation_result import ValidationResult
from ..config import GPS_DECIMAL_PATTERN, GPS_DMS_PATTERN, COMMENT_STYLE_GUIDE


class LocationValidator(BaseValidator):
    """Agent 11: Validate Specific Location field (Column K)"""

    def __init__(self):
        super().__init__('Specific Location', use_ai=False)

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

    def __init__(self):
        super().__init__('Name', use_ai=False)

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
    """Agent 15: Validate Comments field (Column O)

    Uses AI to shorten/standardize comments according to LepSoc style guidelines.
    """

    def __init__(self, llm):
        super().__init__('Comments', llm=llm, use_ai=True)

    def validate(self, value: Any, row_data: Dict = None) -> ValidationResult:
        result = ValidationResult(self.field_name, value)

        # Optional field
        if pd.isna(value) or value == '':
            return result

        comments = str(value).strip()

        # Check for GPS coordinates (both decimal and DMS formats)
        has_decimal_gps = re.search(GPS_DECIMAL_PATTERN, comments)
        has_dms_gps = re.search(GPS_DMS_PATTERN, comments)

        if has_decimal_gps or has_dms_gps:
            result.metadata['has_gps_coords'] = True

        # If exceeds length, use AI to shorten
        if len(comments) > 120:
            result.warnings.append(f"Comments exceed 120 characters: {len(comments)}")

            # Use AI to shorten and standardize
            try:
                shortened = self.execute_ai_task(
                    description=f"Shorten this comment to max 120 characters: '{comments}'",
                    context=COMMENT_STYLE_GUIDE
                )
                result.correction = shortened
                result.metadata['ai_shortened'] = True
            except Exception as e:
                result.errors.append(f"Could not automatically shorten comment: {str(e)}")

        return result
