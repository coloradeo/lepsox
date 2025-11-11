"""
Tests for validation agents
"""
import pytest
from langchain.llms import Ollama
from lepsox.agents import (
    ZoneValidator,
    CountryValidator,
    StateValidator,
    FamilyValidator
)
from lepsox.config import OLLAMA_BASE_URL, OLLAMA_MODEL


@pytest.fixture
def llm():
    """Create Ollama LLM instance"""
    return Ollama(model=OLLAMA_MODEL, base_url=OLLAMA_BASE_URL)


class TestZoneValidator:
    """Tests for ZoneValidator"""

    def test_valid_zone(self, llm):
        validator = ZoneValidator(llm)
        result = validator.validate(8)

        assert result.is_valid
        assert len(result.errors) == 0
        assert result.correction == '8'

    def test_invalid_zone_too_high(self, llm):
        validator = ZoneValidator(llm)
        result = validator.validate(15)

        assert not result.is_valid
        assert any('1-12' in error for error in result.errors)

    def test_invalid_zone_non_numeric(self, llm):
        validator = ZoneValidator(llm)
        result = validator.validate('abc')

        assert not result.is_valid
        assert any('numeric' in error.lower() for error in result.errors)

    def test_missing_zone(self, llm):
        validator = ZoneValidator(llm)
        result = validator.validate('')

        assert not result.is_valid
        assert any('required' in error.lower() for error in result.errors)


class TestCountryValidator:
    """Tests for CountryValidator"""

    def test_valid_country(self, llm):
        validator = CountryValidator(llm)
        result = validator.validate('USA')

        assert result.is_valid
        assert len(result.errors) == 0
        assert result.correction == 'USA'

    def test_lowercase_country(self, llm):
        validator = CountryValidator(llm)
        result = validator.validate('can')

        assert result.is_valid
        assert result.correction == 'CAN'

    def test_invalid_country(self, llm):
        validator = CountryValidator(llm)
        result = validator.validate('UK')

        assert not result.is_valid
        assert any('USA, CAN, or MEX' in error for error in result.errors)


class TestStateValidator:
    """Tests for StateValidator"""

    def test_valid_us_state(self, llm):
        validator = StateValidator(llm)
        row_data = {'Country': 'USA'}
        result = validator.validate('WI', row_data)

        assert result.is_valid
        assert result.correction == 'WI'

    def test_invalid_us_state(self, llm):
        validator = StateValidator(llm)
        row_data = {'Country': 'USA'}
        result = validator.validate('XX', row_data)

        assert not result.is_valid
        assert any('Invalid US state' in error for error in result.errors)

    def test_valid_canadian_province(self, llm):
        validator = StateValidator(llm)
        row_data = {'Country': 'CAN'}
        result = validator.validate('ON', row_data)

        assert result.is_valid


class TestFamilyValidator:
    """Tests for FamilyValidator"""

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
