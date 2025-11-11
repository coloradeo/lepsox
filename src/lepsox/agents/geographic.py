"""
Geographic field validators (Zone, Country, State, County)
"""
from typing import Any, Dict
import pandas as pd

from .base import BaseValidator
from ..models.validation_result import ValidationResult
from ..config import VALID_ZONES, VALID_COUNTRIES, US_STATES, CAN_PROVINCES, MEX_STATES


class ZoneValidator(BaseValidator):
    """Agent 1: Validate Zone field (Column A)"""

    def __init__(self, llm):
        super().__init__('Zone', llm)

    def validate(self, value: Any, row_data: Dict = None) -> ValidationResult:
        result = ValidationResult(self.field_name, value)

        # Check if value exists
        if pd.isna(value) or value == '':
            result.is_valid = False
            result.errors.append("Zone is required")
            return result

        # Convert to int and validate range
        try:
            zone_num = int(value)
            if zone_num not in VALID_ZONES:
                result.is_valid = False
                result.errors.append(f"Zone must be between 1-12, got {zone_num}")
            else:
                result.correction = str(zone_num)  # Ensure string format
        except (ValueError, TypeError):
            result.is_valid = False
            result.errors.append(f"Zone must be numeric, got {value}")

        return result


class CountryValidator(BaseValidator):
    """Agent 2: Validate Country field (Column B)"""

    def __init__(self, llm):
        super().__init__('Country', llm)

    def validate(self, value: Any, row_data: Dict = None) -> ValidationResult:
        result = ValidationResult(self.field_name, value)

        if pd.isna(value) or value == '':
            result.is_valid = False
            result.errors.append("Country is required")
            return result

        value_upper = str(value).upper().strip()

        if value_upper not in VALID_COUNTRIES:
            result.is_valid = False
            result.errors.append(f"Country must be USA, CAN, or MEX, got {value}")

        if len(value_upper) != 3:
            result.is_valid = False
            result.errors.append(f"Country must be exactly 3 characters")

        result.correction = value_upper
        return result


class StateValidator(BaseValidator):
    """Agent 3: Validate State/Province field (Column C)"""

    def __init__(self, llm):
        super().__init__('State', llm)

    def validate(self, value: Any, row_data: Dict = None) -> ValidationResult:
        result = ValidationResult(self.field_name, value)

        if pd.isna(value) or value == '':
            result.is_valid = False
            result.errors.append("State/Province is required")
            return result

        state = str(value).upper().strip()
        country = row_data.get('Country', '').upper() if row_data else ''

        # Validate based on country
        if country == 'USA':
            if state not in US_STATES:
                result.is_valid = False
                result.errors.append(f"Invalid US state: {state}")
        elif country == 'CAN':
            if state not in CAN_PROVINCES:
                result.is_valid = False
                result.errors.append(f"Invalid Canadian province: {state}")
        elif country == 'MEX':
            if state not in MEX_STATES:
                result.warnings.append(f"Please verify Mexican state code: {state}")

        if len(state) > 3:
            result.is_valid = False
            result.errors.append("State/Province must be 3 characters or less")

        result.correction = state
        return result


class CountyValidator(BaseValidator):
    """Agent 8: Validate County field (Column H)"""

    def __init__(self, llm):
        super().__init__('County', llm)

    def validate(self, value: Any, row_data: Dict = None) -> ValidationResult:
        result = ValidationResult(self.field_name, value)

        if pd.isna(value) or value == '':
            result.is_valid = False
            result.errors.append("County is required")
            return result

        county = str(value).strip()

        # Check length
        if len(county) > 20:
            result.is_valid = False
            result.errors.append(f"County exceeds 20 characters: {len(county)}")

        # Should not include "County" suffix
        if 'County' in county or 'Province' in county or 'Territory' in county:
            result.warnings.append("Remove 'County/Province/Territory' from name")
            county_cleaned = county.replace('County', '').replace('Province', '').replace('Territory', '').strip()
            result.correction = county_cleaned

        result.metadata['needs_inat_check'] = True
        return result
