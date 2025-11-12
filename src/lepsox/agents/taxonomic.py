"""
Taxonomic field validators (Family, Genus, Species, Subspecies)
"""
from typing import Any, Dict, Optional
import pandas as pd
import asyncio

from .base import BaseValidator
from ..models.validation_result import ValidationResult


class FamilyValidator(BaseValidator):
    """Agent 4: Validate Family field (Column D)

    Validates family names against iNaturalist taxonomy.
    """

    def __init__(self, llm, inat_validator=None):
        super().__init__('Family', llm=llm, requires="inat")
        self.inat_validator = inat_validator

    def validate(self, value: Any, row_data: Dict = None) -> ValidationResult:
        result = ValidationResult(self.field_name, value)

        if pd.isna(value) or value == '':
            result.is_valid = False
            result.errors.append("Family is required")
            return result

        family = str(value).strip()

        # Normalize to capitalized first letter (e.g., CRAMBIDAE → Crambidae)
        family_normalized = family.capitalize()
        if family != family_normalized:
            result.correction = family_normalized
            result.correction_type = "normalization"  # Case normalization, not a real correction

        # Check length
        if len(family) > 20:
            result.is_valid = False
            result.errors.append(f"Family exceeds 20 characters: {len(family)}")

        # Validate against iNaturalist taxonomy
        if self.inat_validator:
            try:
                # Search for family name in iNat
                inat_result = asyncio.run(
                    self.inat_validator.check_species(family_normalized, "", None)
                )

                if inat_result.get('valid'):
                    # Family found in iNat
                    result.metadata['inat_taxon_id'] = inat_result.get('taxon_id')
                    result.metadata['inat_rank'] = inat_result.get('rank')
                else:
                    # Family not found - mark as ERROR
                    result.is_valid = False
                    result.errors.append(f"Family '{family_normalized}' not found in iNaturalist")
                    result.metadata['needs_human_review'] = True

            except Exception as e:
                result.warnings.append(f"Could not verify family with iNaturalist: {str(e)}")

        return result


class GenusValidator(BaseValidator):
    """Agent 5: Validate Genus field (Column E)"""

    def __init__(self, llm, inat_validator=None):
        super().__init__('Genus', llm=llm, requires="inat")
        self.inat_validator = inat_validator

    def validate(self, value: Any, row_data: Dict = None) -> ValidationResult:
        result = ValidationResult(self.field_name, value)

        if pd.isna(value) or value == '':
            result.is_valid = False
            result.errors.append("Genus is required")
            return result

        genus = str(value).strip()

        # Normalize to capitalized first letter (e.g., DANAUS → Danaus, danaus → Danaus)
        genus_normalized = genus.capitalize()
        if genus != genus_normalized:
            result.correction = genus_normalized
            result.correction_type = "normalization"  # Case normalization, not a real correction

        # Check length
        if len(genus) > 20:
            result.is_valid = False
            result.errors.append(f"Genus exceeds 20 characters: {len(genus)}")

        result.metadata['needs_inat_check'] = True
        return result


class SpeciesValidator(BaseValidator):
    """Agent 6: Validate Species field (Column F)

    Uses iNaturalist API to validate genus/species combinations and suggest
    corrections when hierarchy mismatches are detected.
    """

    def __init__(self, llm, inat_validator=None):
        super().__init__('Species', llm=llm, requires="inat")
        self.inat_validator = inat_validator

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
            result.correction_type = "normalization"  # Case normalization, not a real correction

        # iNaturalist validation if validator is provided
        if self.inat_validator and row_data:
            genus = row_data.get('Genus', '')
            family = row_data.get('Family', '')

            if genus:
                try:
                    # Run async check synchronously
                    inat_result = asyncio.run(
                        self.inat_validator.check_species(genus, species, family)
                    )

                    if inat_result.get('valid'):
                        # Species found in iNat
                        taxon_id = inat_result.get('taxon_id')
                        result.metadata['inat_taxon_id'] = taxon_id
                        result.metadata['inat_common_name'] = inat_result.get('common_name')

                        # Store in row_data for use by record validators
                        if row_data is not None:
                            row_data['_inat_taxon_id'] = taxon_id

                        # Check hierarchy
                        if inat_result.get('hierarchy_mismatch'):
                            result.warnings.append(
                                f"Family mismatch: '{family}' should be '{inat_result['suggested_family']}' "
                                f"based on genus/species"
                            )
                            result.metadata['suggested_family'] = inat_result['suggested_family']

                    else:
                        # Species not found - mark as ERROR
                        result.is_valid = False
                        result.errors.append(f"Species '{genus} {species}' not found in iNaturalist")
                        result.metadata['needs_human_review'] = True

                except Exception as e:
                    result.warnings.append(f"Could not verify with iNaturalist: {str(e)}")

        return result


class SubspeciesValidator(BaseValidator):
    """Agent 7: Validate Sub-species field (Column G)

    Uses iNaturalist API to validate genus/species/subspecies trinomial combinations.
    """

    def __init__(self, llm, inat_validator=None):
        super().__init__('Sub-species', llm=llm, requires="inat")
        self.inat_validator = inat_validator

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
            result.correction_type = "normalization"  # Case normalization, not a real correction

        # iNaturalist validation for trinomial name if validator is provided
        if self.inat_validator and row_data:
            genus = row_data.get('Genus', '')
            species = row_data.get('Species', '')
            family = row_data.get('Family', '')

            if genus and species and subspecies:
                try:
                    # Validate trinomial name: genus species subspecies
                    trinomial = f"{genus} {species} {subspecies}"
                    inat_result = asyncio.run(
                        self.inat_validator.check_species(genus, f"{species} {subspecies}", family)
                    )

                    if inat_result.get('valid'):
                        # Trinomial found in iNat
                        result.metadata['inat_taxon_id'] = inat_result.get('taxon_id')
                        result.metadata['inat_common_name'] = inat_result.get('common_name')
                        result.metadata['validated_trinomial'] = trinomial

                        # Check hierarchy
                        if inat_result.get('hierarchy_mismatch'):
                            result.warnings.append(
                                f"Family mismatch: '{family}' should be '{inat_result['suggested_family']}' "
                                f"based on trinomial name"
                            )
                            result.metadata['suggested_family'] = inat_result['suggested_family']
                    else:
                        # Trinomial not found - mark as ERROR
                        result.is_valid = False
                        result.errors.append(
                            f"Subspecies '{trinomial}' not found in iNaturalist"
                        )
                        result.metadata['needs_human_review'] = True

                except Exception as e:
                    result.warnings.append(f"Could not verify subspecies with iNaturalist: {str(e)}")

        return result
