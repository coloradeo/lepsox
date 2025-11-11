"""
Base validator class for all field validators
"""
from typing import Any, Dict
from crewai import Agent

from ..models.validation_result import ValidationResult


class BaseValidator(Agent):
    """Base class for all validation agents"""

    def __init__(self, field_name: str, llm):
        self.field_name = field_name
        super().__init__(
            role=f'{field_name} Validator',
            goal=f'Validate {field_name} field according to LepSoc standards',
            backstory=f'Expert validator for {field_name} in Lepidopterist Society data',
            llm=llm,
            allow_delegation=False,
            verbose=True
        )

    def validate(self, value: Any, row_data: Dict = None) -> ValidationResult:
        """
        Validate a field value.
        Override this method in subclasses to implement field-specific validation.

        Args:
            value: The value to validate
            row_data: Optional dictionary of the full row data for cross-field validation

        Returns:
            ValidationResult: Result object containing validation status and details
        """
        result = ValidationResult(self.field_name, value)
        return result
