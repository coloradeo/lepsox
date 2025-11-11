"""
Tests for validation agents

Tests the hybrid validator architecture with both deterministic
and AI-powered validators.
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from langchain.llms import Ollama

from lepsox.agents import (
    ZoneValidator,
    CountryValidator,
    StateValidator,
    CountyValidator,
    FamilyValidator,
    GenusValidator,
    SpeciesValidator,
    SubspeciesValidator,
    FirstDateValidator,
    LastDateValidator,
    YearValidator,
    StateRecordValidator,
    CountyRecordValidator,
    LocationValidator,
    NameValidator,
    CommentValidator
)
from lepsox.integrations import INatValidator
from lepsox.config import OLLAMA_BASE_URL, OLLAMA_MODEL


@pytest.fixture
def llm():
    """Create Ollama LLM instance for AI-powered validators"""
    return Ollama(model=OLLAMA_MODEL, base_url=OLLAMA_BASE_URL)


@pytest.fixture
def mock_inat_validator():
    """Create mock iNaturalist validator"""
    validator = Mock(spec=INatValidator)

    # Mock successful species check
    async def mock_check_species(genus, species, family=None):
        return {
            'valid': True,
            'taxon_id': 12345,
            'correct_name': f"{genus} {species}",
            'common_name': 'Test Species',
            'family': family,
            'genus': genus,
            'species': species
        }

    # Mock successful location check
    async def mock_check_location(county, state, country):
        return {
            'valid': True,
            'place_id': 67890,
            'display_name': f"{county}, {state}, {country}"
        }

    validator.check_species = AsyncMock(side_effect=mock_check_species)
    validator.check_location = AsyncMock(side_effect=mock_check_location)

    return validator


# ============================================================================
# DETERMINISTIC VALIDATORS (no LLM required)
# ============================================================================

class TestZoneValidator:
    """Tests for ZoneValidator (deterministic)"""

    def test_valid_zone(self):
        validator = ZoneValidator()
        result = validator.validate(8)

        assert result.is_valid
        assert len(result.errors) == 0
        assert result.correction == '8'

    def test_invalid_zone_too_high(self):
        validator = ZoneValidator()
        result = validator.validate(15)

        assert not result.is_valid
        assert any('1-12' in error for error in result.errors)

    def test_invalid_zone_non_numeric(self):
        validator = ZoneValidator()
        result = validator.validate('abc')

        assert not result.is_valid
        assert any('numeric' in error.lower() for error in result.errors)

    def test_missing_zone(self):
        validator = ZoneValidator()
        result = validator.validate('')

        assert not result.is_valid
        assert any('required' in error.lower() for error in result.errors)

    def test_zone_uses_no_ai(self):
        """Verify ZoneValidator doesn't initialize as Agent"""
        validator = ZoneValidator()
        assert not validator.use_ai


class TestCountryValidator:
    """Tests for CountryValidator (deterministic)"""

    def test_valid_country(self):
        validator = CountryValidator()
        result = validator.validate('USA')

        assert result.is_valid
        assert len(result.errors) == 0
        assert result.correction == 'USA'

    def test_lowercase_country(self):
        validator = CountryValidator()
        result = validator.validate('can')

        assert result.is_valid
        assert result.correction == 'CAN'

    def test_invalid_country(self):
        validator = CountryValidator()
        result = validator.validate('UK')

        assert not result.is_valid
        assert any('USA, CAN, or MEX' in error for error in result.errors)

    def test_country_uses_no_ai(self):
        """Verify CountryValidator doesn't initialize as Agent"""
        validator = CountryValidator()
        assert not validator.use_ai


class TestStateValidator:
    """Tests for StateValidator (deterministic)"""

    def test_valid_us_state(self):
        validator = StateValidator()
        row_data = {'Country': 'USA'}
        result = validator.validate('WI', row_data)

        assert result.is_valid
        assert result.correction == 'WI'

    def test_invalid_us_state(self):
        validator = StateValidator()
        row_data = {'Country': 'USA'}
        result = validator.validate('XX', row_data)

        assert not result.is_valid
        assert any('Invalid US state' in error for error in result.errors)

    def test_valid_canadian_province(self):
        validator = StateValidator()
        row_data = {'Country': 'CAN'}
        result = validator.validate('ON', row_data)

        assert result.is_valid

    def test_state_uses_no_ai(self):
        """Verify StateValidator doesn't initialize as Agent"""
        validator = StateValidator()
        assert not validator.use_ai


class TestCountyValidator:
    """Tests for CountyValidator (deterministic with optional iNat)"""

    def test_valid_county(self):
        validator = CountyValidator()
        result = validator.validate('Dane')

        assert result.is_valid
        assert len(result.errors) == 0

    def test_county_with_suffix(self):
        validator = CountyValidator()
        result = validator.validate('Dane County')

        assert result.is_valid
        assert result.correction == 'Dane'
        assert any('County' in warning for warning in result.warnings)

    def test_county_with_inat_validation(self, mock_inat_validator):
        validator = CountyValidator(mock_inat_validator)
        row_data = {'State': 'WI', 'Country': 'USA'}
        result = validator.validate('Dane', row_data)

        assert result.is_valid
        assert 'inat_place_id' in result.metadata

    def test_county_uses_no_ai(self):
        """Verify CountyValidator doesn't initialize as Agent"""
        validator = CountyValidator()
        assert not validator.use_ai


class TestFirstDateValidator:
    """Tests for FirstDateValidator (deterministic)"""

    def test_valid_date(self):
        validator = FirstDateValidator()
        result = validator.validate('15-JUL-24')

        assert result.is_valid
        assert len(result.errors) == 0

    def test_invalid_date_format(self):
        validator = FirstDateValidator()
        result = validator.validate('07/15/2024')

        assert not result.is_valid
        assert any('dd-mmm-yy' in error.lower() for error in result.errors)

    def test_date_uses_no_ai(self):
        """Verify FirstDateValidator doesn't initialize as Agent"""
        validator = FirstDateValidator()
        assert not validator.use_ai


class TestYearValidator:
    """Tests for YearValidator (deterministic)"""

    def test_valid_year(self):
        validator = YearValidator()
        result = validator.validate(2024)

        assert result.is_valid

    def test_invalid_year_future(self):
        validator = YearValidator()
        result = validator.validate(2099)

        assert not result.is_valid
        assert any('future' in error.lower() for error in result.errors)

    def test_year_uses_no_ai(self):
        """Verify YearValidator doesn't initialize as Agent"""
        validator = YearValidator()
        assert not validator.use_ai


# ============================================================================
# AI-POWERED VALIDATORS (require LLM)
# ============================================================================

class TestFamilyValidator:
    """Tests for FamilyValidator (AI-powered)"""

    def test_valid_family(self, llm):
        validator = FamilyValidator(llm)
        result = validator.validate('Nymphalidae')

        assert result.is_valid
        assert len(result.errors) == 0

    def test_uncommon_family(self, llm):
        validator = FamilyValidator(llm)
        result = validator.validate('UnknownFamily')

        assert result.is_valid  # Still valid, just with warning
        assert len(result.warnings) > 0
        assert result.metadata.get('needs_inat_check')

    def test_family_too_long(self, llm):
        validator = FamilyValidator(llm)
        result = validator.validate('A' * 25)

        assert not result.is_valid
        assert any('exceeds 20 characters' in error for error in result.errors)

    def test_family_uses_ai(self, llm):
        """Verify FamilyValidator initializes as Agent"""
        validator = FamilyValidator(llm)
        assert validator.use_ai


class TestGenusValidator:
    """Tests for GenusValidator (AI-powered)"""

    def test_valid_genus(self, llm):
        validator = GenusValidator(llm)
        result = validator.validate('Danaus')

        assert result.is_valid

    def test_genus_capitalization(self, llm):
        validator = GenusValidator(llm)
        result = validator.validate('danaus')

        assert result.is_valid
        assert result.correction == 'Danaus'
        assert len(result.warnings) > 0

    def test_genus_uses_ai(self, llm):
        """Verify GenusValidator initializes as Agent"""
        validator = GenusValidator(llm)
        assert validator.use_ai


class TestSpeciesValidator:
    """Tests for SpeciesValidator (AI-powered with iNat)"""

    def test_valid_species(self, llm):
        validator = SpeciesValidator(llm)
        result = validator.validate('plexippus')

        assert result.is_valid

    def test_species_with_inat_validation(self, llm, mock_inat_validator):
        validator = SpeciesValidator(llm, mock_inat_validator)
        row_data = {'Genus': 'Danaus', 'Family': 'Nymphalidae'}
        result = validator.validate('plexippus', row_data)

        assert result.is_valid
        assert 'inat_taxon_id' in result.metadata
        assert 'inat_common_name' in result.metadata

    def test_species_hierarchy_mismatch(self, llm):
        """Test detection of family/genus/species mismatch"""
        validator = SpeciesValidator(llm)

        # Mock iNat validator that returns hierarchy mismatch
        mock_inat = Mock(spec=INatValidator)

        async def mock_check_with_mismatch(genus, species, family):
            return {
                'valid': True,
                'taxon_id': 12345,
                'hierarchy_mismatch': True,
                'suggested_family': 'Papilionidae'
            }

        mock_inat.check_species = AsyncMock(side_effect=mock_check_with_mismatch)
        validator.inat_validator = mock_inat

        row_data = {'Genus': 'Papilio', 'Family': 'Nymphalidae'}
        result = validator.validate('glaucus', row_data)

        assert result.is_valid
        assert len(result.warnings) > 0
        assert 'suggested_family' in result.metadata
        assert result.metadata['suggested_family'] == 'Papilionidae'

    def test_species_uses_ai(self, llm):
        """Verify SpeciesValidator initializes as Agent"""
        validator = SpeciesValidator(llm)
        assert validator.use_ai


class TestSubspeciesValidator:
    """Tests for SubspeciesValidator (AI-powered with iNat)"""

    def test_subspecies_optional(self, llm):
        validator = SubspeciesValidator(llm)
        result = validator.validate('')

        assert result.is_valid

    def test_valid_subspecies(self, llm):
        validator = SubspeciesValidator(llm)
        result = validator.validate('megalippe')

        assert result.is_valid

    def test_subspecies_with_inat_validation(self, llm, mock_inat_validator):
        validator = SubspeciesValidator(llm, mock_inat_validator)
        row_data = {
            'Genus': 'Danaus',
            'Species': 'plexippus',
            'Family': 'Nymphalidae'
        }
        result = validator.validate('megalippe', row_data)

        assert result.is_valid
        assert 'validated_trinomial' in result.metadata
        assert result.metadata['validated_trinomial'] == 'Danaus plexippus megalippe'

    def test_subspecies_uses_ai(self, llm):
        """Verify SubspeciesValidator initializes as Agent"""
        validator = SubspeciesValidator(llm)
        assert validator.use_ai


class TestCommentValidator:
    """Tests for CommentValidator (AI-powered)"""

    def test_valid_short_comment(self, llm):
        validator = CommentValidator(llm)
        result = validator.validate('nect on milkweed')

        assert result.is_valid
        assert len(result.errors) == 0

    def test_gps_detection_decimal(self, llm):
        validator = CommentValidator(llm)
        result = validator.validate('Found at 42.5834,-87.8294')

        assert result.is_valid
        assert result.metadata.get('has_gps_coords')

    def test_gps_detection_dms(self, llm):
        validator = CommentValidator(llm)
        result = validator.validate('Location: 42°35\'2.4"N 87°49\'45.6"W')

        assert result.is_valid
        assert result.metadata.get('has_gps_coords')

    def test_long_comment_triggers_warning(self, llm):
        validator = CommentValidator(llm)
        long_comment = 'A' * 150
        result = validator.validate(long_comment)

        # Will have warning about length
        assert len(result.warnings) > 0
        assert any('120 characters' in warning for warning in result.warnings)

    def test_comment_uses_ai(self, llm):
        """Verify CommentValidator initializes as Agent"""
        validator = CommentValidator(llm)
        assert validator.use_ai


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestHybridArchitecture:
    """Tests for hybrid validator architecture"""

    def test_deterministic_validators_count(self):
        """Verify 11 validators don't require LLM"""
        deterministic = [
            ZoneValidator(),
            CountryValidator(),
            StateValidator(),
            CountyValidator(),
            FirstDateValidator(),
            LastDateValidator(),
            YearValidator(),
            StateRecordValidator(),
            CountyRecordValidator(),
            LocationValidator(),
            NameValidator()
        ]

        for validator in deterministic:
            assert not validator.use_ai, f"{validator.field_name} should not use AI"

    def test_ai_validators_count(self, llm):
        """Verify 5 validators require LLM"""
        ai_powered = [
            FamilyValidator(llm),
            GenusValidator(llm),
            SpeciesValidator(llm),
            SubspeciesValidator(llm),
            CommentValidator(llm)
        ]

        for validator in ai_powered:
            assert validator.use_ai, f"{validator.field_name} should use AI"

    def test_inat_validators_have_validator(self, llm, mock_inat_validator):
        """Verify taxonomic validators have iNat validator"""
        taxonomic = [
            FamilyValidator(llm, mock_inat_validator),
            GenusValidator(llm, mock_inat_validator),
            SpeciesValidator(llm, mock_inat_validator),
            SubspeciesValidator(llm, mock_inat_validator)
        ]

        for validator in taxonomic:
            assert validator.inat_validator is not None
