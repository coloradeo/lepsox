"""
LepSoc Season Summary Validation System
A CrewAI-powered validation system for Lepidopterist Society observation data.
"""

__version__ = "0.1.0"
__author__ = "Eric Olson"

from .validator import LepSocValidationCrew
from .models.validation_result import ValidationResult

__all__ = ["LepSocValidationCrew", "ValidationResult"]
