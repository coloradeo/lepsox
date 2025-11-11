"""
Taxonomic field validators (Family, Genus, Species, Subspecies)
"""
from typing import Any, Dict
import pandas as pd

from .base import BaseValidator
from ..models.validation_result import ValidationResult
from ..config import COMMON_FAMILIES


class FamilyValidator(BaseValidator):
    """Agent 4: Validate Family field (Column D)"""

    def __init__(self, llm):
        super().__init__('Family', llm)

    def validate(self, value: Any, row_data: Dict = None) -> ValidationResult:
        result = ValidationResult(self.field_name, value)

        if pd.isna(value) or value == '':
            result.is_valid = False
            result.errors.append("Family is required")
            return result

        family = str(value).strip()

        # Check length
        if len(family) > 20:
            result.is_valid = False
            result.errors.append(f"Family exceeds 20 characters: {len(family)}")

        # Check if it's a known Lepidoptera family
        if family not in COMMON_FAMILIES:
            result.warnings.append(f"Uncommon family name: {family}. Please verify.")
            result.metadata['needs_inat_check'] = True

        return result


class GenusValidator(BaseValidator):
    """Agent 5: Validate Genus field (Column E)"""

    def __init__(self, llm):
        super().__init__('Genus', llm)

    def validate(self, value: Any, row_data: Dict = None) -> ValidationResult:
        result = ValidationResult(self.field_name, value)

        if pd.isna(value) or value == '':
            result.is_valid = False
            result.errors.append("Genus is required")
            return result

        genus = str(value).strip()

        # Check length
        if len(genus) > 20:
            result.is_valid = False
            result.errors.append(f"Genus exceeds 20 characters: {len(genus)}")

        # Check capitalization
        if genus and not genus[0].isupper():
            result.warnings.append("Genus should start with capital letter")
            result.correction = genus.capitalize()

        result.metadata['needs_inat_check'] = True
        return result


class SpeciesValidator(BaseValidator):
    """Agent 6: Validate Species field (Column F)"""

    def __init__(self, llm):
        super().__init__('Species', llm)

    def validate(self, value: Any, row_data: Dict = None) -> ValidationResult:
        result = ValidationResult(self.field_name, value)

        if pd.isna(value) or value == '':
            result.is_valid = False
            result.errors.append("Species is required")
            return result

        species = str(value).strip().lower()

        # Check length
        if len(species) > 18:
            result.is_valid = False
            result.errors.append(f"Species exceeds 18 characters: {len(species)}")

        # Species epithet should be lowercase
        if species != str(value).strip():
            result.correction = species

        result.metadata['needs_inat_check'] = True
        return result


class SubspeciesValidator(BaseValidator):
    """Agent 7: Validate Sub-species field (Column G)"""

    def __init__(self, llm):
        super().__init__('Sub-species', llm)

    def validate(self, value: Any, row_data: Dict = None) -> ValidationResult:
        result = ValidationResult(self.field_name, value)

        # Optional field
        if pd.isna(value) or value == '':
            return result

        subspecies = str(value).strip().lower()

        # Check length
        if len(subspecies) > 16:
            result.is_valid = False
            result.errors.append(f"Sub-species exceeds 16 characters: {len(subspecies)}")

        # Should be lowercase
        if subspecies != str(value).strip():
            result.correction = subspecies

        return result
