"""
Record detection validators (State Record, County Record)
"""
from typing import Any, Dict
import pandas as pd
import asyncio

from .base import BaseValidator
from ..models.validation_result import ValidationResult


class StateRecordValidator(BaseValidator):
    """Agent 9: Validate State Record field (Column I)

    Checks iNaturalist to verify if this is actually a state record
    (no prior observations for this taxon in this state).
    """

    def __init__(self, inat_validator=None):
        super().__init__('State Record')
        self.inat_validator = inat_validator

    def validate(self, value: Any, row_data: Dict = None) -> ValidationResult:
        result = ValidationResult(self.field_name, value)

        # Optional field
        value_upper = ''
        if not (pd.isna(value) or value == ''):
            value_upper = str(value).upper().strip()

            if value_upper not in ['Y', 'N']:
                result.is_valid = False
                result.errors.append("State Record must be Y, N, or blank")
                return result

            # Only normalize case if value changed
            if str(value).strip() != value_upper:
                result.correction = value_upper
                result.correction_type = "normalization"  # Case normalization, not a real correction

        # Check if species is valid first - if not, we can't verify state records
        if row_data and not row_data.get('_inat_taxon_id'):
            # Species is invalid - mark as warning and don't auto-fill
            if value_upper == '':
                result.warnings.append("Cannot verify state record - species not found in iNaturalist")
            return result

        # Verify against iNaturalist if possible
        if self.inat_validator and row_data:
            # Need taxon_id from species validation and state
            taxon_id = row_data.get('_inat_taxon_id')  # Set by SpeciesValidator
            state = row_data.get('State', '')

            if taxon_id and state:
                try:
                    # Check if there are existing observations in this state
                    inat_result = asyncio.run(
                        self.inat_validator.check_record_status(
                            taxon_id=taxon_id,
                            state=state
                        )
                    )

                    if not inat_result.get('error'):
                        is_new_record = inat_result.get('is_new_record', False)
                        existing_count = inat_result.get('existing_count', 0)

                        # Compare with user's marking
                        if value_upper == 'Y' and not is_new_record:
                            # User says it's a record but iNat shows existing observations → ERROR
                            result.is_valid = False
                            result.errors.append(
                                f"Marked as state record but {existing_count} observations already exist in iNaturalist"
                            )
                        elif value_upper == 'N' and is_new_record:
                            # User says it's NOT a record but iNat shows no observations → ERROR
                            result.is_valid = False
                            result.errors.append(
                                "Marked as NOT a state record but no prior observations found in iNaturalist"
                            )
                            result.correction = 'Y'
                            result.correction_type = "correction"  # Fixing incorrect user value
                        elif value_upper == '':
                            # Auto-fill based on iNat check (always fill Y or N)
                            result.correction = 'Y' if is_new_record else 'N'
                            # Only mark as correction (orange) if it's a new record (Y)
                            # Default N is just normalization (no color)
                            result.correction_type = "correction" if is_new_record else "normalization"
                            if is_new_record:
                                result.warnings.append(
                                    "Auto-filled as state record (no prior observations in iNaturalist)"
                                )
                            # Note: When auto-filling as 'N', no warning per user request

                        result.metadata['inat_existing_count'] = existing_count
                        result.metadata['inat_query_url'] = inat_result.get('query_url', '')
                    else:
                        # iNat check returned an error - default to 'N' if blank
                        if value_upper == '':
                            result.correction = 'N'
                            result.correction_type = "normalization"  # Default N is not a meaningful correction
                            result.warnings.append(f"Could not verify state record: {inat_result.get('error')}")

                except Exception as e:
                    result.warnings.append(f"Could not verify state record with iNaturalist: {str(e)}")
                    # If iNat check failed and field is blank, default to 'N'
                    if value_upper == '':
                        result.correction = 'N'
                        result.correction_type = "normalization"  # Default N is not a meaningful correction
            else:
                # Missing taxon_id or state - can't check iNat, default to 'N' if blank
                if value_upper == '':
                    result.correction = 'N'
                    result.correction_type = "normalization"  # Default N is not a meaningful correction
        else:
            # No iNat validator available - default to 'N' if blank
            if value_upper == '':
                result.correction = 'N'
                result.correction_type = "normalization"  # Default N is not a meaningful correction

        return result


class CountyRecordValidator(BaseValidator):
    """Agent 10: Validate County Record field (Column J)

    Checks iNaturalist to verify if this is actually a county record
    (no prior observations for this taxon in this county).
    """

    def __init__(self, inat_validator=None):
        super().__init__('County Record')
        self.inat_validator = inat_validator

    def validate(self, value: Any, row_data: Dict = None) -> ValidationResult:
        result = ValidationResult(self.field_name, value)

        # Optional field
        value_upper = ''
        if not (pd.isna(value) or value == ''):
            value_upper = str(value).upper().strip()

            if value_upper not in ['Y', 'N']:
                result.is_valid = False
                result.errors.append("County Record must be Y, N, or blank")
                return result

            # Only normalize case if value changed
            if str(value).strip() != value_upper:
                result.correction = value_upper
                result.correction_type = "normalization"  # Case normalization, not a real correction

        # Check if species is valid first - if not, we can't verify county records
        if row_data and not row_data.get('_inat_taxon_id'):
            # Species is invalid - mark as warning and don't auto-fill
            if value_upper == '':
                result.warnings.append("Cannot verify county record - species not found in iNaturalist")
            return result

        # Verify against iNaturalist if possible
        if self.inat_validator and row_data:
            # Need taxon_id and place_id (county)
            taxon_id = row_data.get('_inat_taxon_id')  # Set by SpeciesValidator
            place_id = row_data.get('_inat_place_id')  # Set by CountyValidator
            county = row_data.get('County', '')
            state = row_data.get('State', '')

            if taxon_id and place_id:
                try:
                    # Check if there are existing observations in this county
                    inat_result = asyncio.run(
                        self.inat_validator.check_record_status(
                            taxon_id=taxon_id,
                            place_id=place_id,
                            county=county,
                            state=state
                        )
                    )

                    if not inat_result.get('error'):
                        is_new_record = inat_result.get('is_new_record', False)
                        existing_count = inat_result.get('existing_count', 0)

                        # Compare with user's marking
                        if value_upper == 'Y' and not is_new_record:
                            # User says it's a record but iNat shows existing observations → ERROR
                            result.is_valid = False
                            result.errors.append(
                                f"Marked as county record but {existing_count} observations already exist in iNaturalist"
                            )
                        elif value_upper == 'N' and is_new_record:
                            # User says it's NOT a record but iNat shows no observations → ERROR
                            result.is_valid = False
                            result.errors.append(
                                "Marked as NOT a county record but no prior observations found in iNaturalist"
                            )
                            result.correction = 'Y'
                            result.correction_type = "correction"  # Fixing incorrect user value
                        elif value_upper == '':
                            # Auto-fill based on iNat check (always fill Y or N)
                            result.correction = 'Y' if is_new_record else 'N'
                            # Only mark as correction (orange) if it's a new record (Y)
                            # Default N is just normalization (no color)
                            result.correction_type = "correction" if is_new_record else "normalization"
                            if is_new_record:
                                result.warnings.append(
                                    "Auto-filled as county record (no prior observations in iNaturalist)"
                                )
                            # Note: When auto-filling as 'N', no warning per user request

                        result.metadata['inat_existing_count'] = existing_count
                        result.metadata['inat_query_url'] = inat_result.get('query_url', '')
                    else:
                        # iNat check returned an error - default to 'N' if blank
                        if value_upper == '':
                            result.correction = 'N'
                            result.correction_type = "normalization"  # Default N is not a meaningful correction
                            result.warnings.append(f"Could not verify county record: {inat_result.get('error')}")

                except Exception as e:
                    result.warnings.append(f"Could not verify county record with iNaturalist: {str(e)}")
                    # If iNat check failed and field is blank, default to 'N'
                    if value_upper == '':
                        result.correction = 'N'
                        result.correction_type = "normalization"  # Default N is not a meaningful correction
            else:
                # Missing taxon_id or place_id - can't check iNat, default to 'N' if blank
                if value_upper == '':
                    result.correction = 'N'
                    result.correction_type = "normalization"  # Default N is not a meaningful correction
        else:
            # No iNat validator available - default to 'N' if blank
            if value_upper == '':
                result.correction = 'N'
                result.correction_type = "normalization"  # Default N is not a meaningful correction

        return result
