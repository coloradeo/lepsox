"""
Temporal field validators (First Date, Last Date, Year)
"""
from typing import Any, Dict
import pandas as pd
import re
from datetime import datetime

from .base import BaseValidator
from ..models.validation_result import ValidationResult
from ..config import DATE_FORMAT


class FirstDateValidator(BaseValidator):
    """Agent 12: Validate First Date field (Column L)"""

    def __init__(self, llm):
        super().__init__('First Date', llm)

    def validate(self, value: Any, row_data: Dict = None) -> ValidationResult:
        result = ValidationResult(self.field_name, value)

        if pd.isna(value) or value == '':
            result.is_valid = False
            result.errors.append("First Date is required")
            return result

        date_str = str(value).strip()

        # Check format dd-mmm-yy
        if not re.match(DATE_FORMAT, date_str.upper()):
            result.is_valid = False
            result.errors.append(f"Date format must be dd-mmm-yy, got {date_str}")

        # Check if date is reasonable (within last 3 years)
        try:
            # Parse date
            date_parts = date_str.split('-')
            if len(date_parts) == 3:
                year = int(date_parts[2])
                # Convert 2-digit year to 4-digit
                if year < 100:
                    year = 2000 + year if year < 50 else 1900 + year

                current_year = datetime.now().year
                if current_year - year > 3:
                    result.warnings.append(f"Date is more than 3 years old: {year}")
        except:
            pass

        return result


class LastDateValidator(BaseValidator):
    """Agent 13: Validate Last Date field (Column M)"""

    def __init__(self, llm):
        super().__init__('Last Date', llm)

    def validate(self, value: Any, row_data: Dict = None) -> ValidationResult:
        result = ValidationResult(self.field_name, value)

        # Optional field
        if pd.isna(value) or value == '':
            return result

        date_str = str(value).strip()

        # Check format
        if not re.match(DATE_FORMAT, date_str.upper()):
            result.is_valid = False
            result.errors.append(f"Date format must be dd-mmm-yy, got {date_str}")

        # TODO: Compare with First Date to ensure Last >= First

        return result


class YearValidator(BaseValidator):
    """Agent 16: Validate Year field (Column P)"""

    def __init__(self, llm):
        super().__init__('Year', llm)

    def validate(self, value: Any, row_data: Dict = None) -> ValidationResult:
        result = ValidationResult(self.field_name, value)

        if pd.isna(value) or value == '':
            result.is_valid = False
            result.errors.append("Year is required")
            return result

        try:
            year = int(value)

            if year < 1000 or year > 9999:
                result.is_valid = False
                result.errors.append(f"Year must be 4 digits")

            current_year = datetime.now().year
            if current_year - year > 3:
                result.warnings.append(f"Year is more than 3 years old: {year}")

            if year > current_year:
                result.is_valid = False
                result.errors.append(f"Year cannot be in the future: {year}")

        except (ValueError, TypeError):
            result.is_valid = False
            result.errors.append(f"Year must be numeric: {value}")

        return result
