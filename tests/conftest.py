"""
Pytest configuration and fixtures
"""
import pytest
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from lepsox import LepSocValidationCrew
from lepsox.models import ValidationResult


@pytest.fixture
def sample_valid_file():
    """Path to valid sample file"""
    return Path(__file__).parent / "fixtures" / "valid_sample.xlsx"


@pytest.fixture
def sample_error_file():
    """Path to sample file with errors"""
    return Path(__file__).parent / "fixtures" / "test_with_errors.xlsx"


@pytest.fixture
def validator_crew():
    """Create a validation crew instance"""
    return LepSocValidationCrew()


@pytest.fixture
def mock_row_data():
    """Sample row data for testing"""
    return {
        'Zone': '8',
        'Country': 'USA',
        'State': 'WI',
        'Family': 'Nymphalidae',
        'Genus': 'Danaus',
        'Species': 'plexippus',
        'Sub-species': '',
        'County': 'Door',
        'State Record': '',
        'County Record': '',
        'Specific Location': 'Peninsula State Park',
        'First Date': '15-JUL-24',
        'Last Date': '',
        'Name': 'ABC',
        'Comments': '',
        'Year': '2024'
    }
