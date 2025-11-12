"""
Geographic field validators (Zone, Country, State, County)
"""
from typing import Any, Dict, Optional
import pandas as pd
import asyncio

from .base import BaseValidator
from ..models.validation_result import ValidationResult
from ..config import VALID_ZONES, VALID_COUNTRIES, US_STATES, CAN_PROVINCES, MEX_STATES


class ZoneValidator(BaseValidator):
    """Agent 1: Validate Zone field (Column A)"""

    def __init__(self):
        super().__init__('Zone')

    def validate(self, value: Any, row_data: Dict = None) -> ValidationResult:
        result = ValidationResult(self.field_name, value)

        # Check if value exists
        if pd.isna(value) or value == '':
            # Check if this is an empty row (missing Zone, Country, State)
            if row_data:
                country = row_data.get('Country', '')
                state = row_data.get('State', '')
                is_empty_row = (pd.isna(country) or country == '') and (pd.isna(state) or state == '')

                if is_empty_row:
                    # Empty row - mark as warning instead of error
                    result.warnings.append("Zone is missing (empty row)")
                    return result

            # Not an empty row - missing required field is an error
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
                result.correction = zone_num  # Keep as integer for Excel
                result.correction_type = "normalization"  # Type conversion, not a real correction
        except (ValueError, TypeError):
            result.is_valid = False
            result.errors.append(f"Zone must be numeric, got {value}")

        return result


class CountryValidator(BaseValidator):
    """Agent 2: Validate Country field (Column B)"""

    def __init__(self):
        super().__init__('Country')

    def validate(self, value: Any, row_data: Dict = None) -> ValidationResult:
        result = ValidationResult(self.field_name, value)

        if pd.isna(value) or value == '':
            # Check if this is an empty row (missing Zone, Country, State)
            if row_data:
                zone = row_data.get('Zone', '')
                state = row_data.get('State', '')
                is_empty_row = (pd.isna(zone) or zone == '') and (pd.isna(state) or state == '')

                if is_empty_row:
                    # Empty row - mark as warning instead of error
                    result.warnings.append("Country is missing (empty row)")
                    return result

            # Not an empty row - missing required field is an error
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
        result.correction_type = "normalization"  # Case normalization, not a real correction
        return result


class StateValidator(BaseValidator):
    """Agent 3: Validate State/Province field (Column C)"""

    def __init__(self):
        super().__init__('State')

    def validate(self, value: Any, row_data: Dict = None) -> ValidationResult:
        result = ValidationResult(self.field_name, value)

        if pd.isna(value) or value == '':
            # Check if this is an empty row (missing Zone, Country, State)
            if row_data:
                zone = row_data.get('Zone', '')
                country = row_data.get('Country', '')
                is_empty_row = (pd.isna(zone) or zone == '') and (pd.isna(country) or country == '')

                if is_empty_row:
                    # Empty row - mark as warning instead of error
                    result.warnings.append("State is missing (empty row)")
                    return result

            # Not an empty row - missing required field is an error
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
        result.correction_type = "normalization"  # Case normalization, not a real correction
        return result


class CountyValidator(BaseValidator):
    """Agent 8: Validate County field (Column H)

    Uses iNaturalist to verify County/State/Country alignment.
    """

    def __init__(self, inat_validator=None):
        super().__init__('County')
        self.inat_validator = inat_validator

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
            result.correction_type = "correction"  # Actual correction - removing suffix
            county = county_cleaned

        # iNaturalist validation if validator is provided
        if self.inat_validator and row_data:
            state = row_data.get('State', '')
            country = row_data.get('Country', '')

            if state and country:
                try:
                    # Run async check synchronously
                    inat_result = asyncio.run(
                        self.inat_validator.check_location(county, state, country)
                    )

                    if inat_result.get('valid'):
                        # Location found in iNat
                        place_id = inat_result.get('place_id')
                        result.metadata['inat_place_id'] = place_id
                        result.metadata['inat_display_name'] = inat_result.get('display_name')

                        # Store in row_data for use by record validators
                        if row_data is not None:
                            row_data['_inat_place_id'] = place_id
                    else:
                        # Location not found
                        result.warnings.append(
                            f"Location '{county}, {state}, {country}' not found in iNaturalist"
                        )
                        result.metadata['needs_human_review'] = True

                except Exception as e:
                    result.warnings.append(f"Could not verify location with iNaturalist: {str(e)}")

        return result
