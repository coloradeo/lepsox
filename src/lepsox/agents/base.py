"""
Base validator class for all field validators

Supports both deterministic (pure Python) and AI-powered validation.
"""
from typing import Any, Dict, Optional
from crewai import Agent, Task

from ..models.validation_result import ValidationResult


class BaseValidator:
    """
    Base class for all validation agents

    Supports both deterministic and AI-powered validation:
    - use_ai=False: Simple Python logic, fast, no LLM needed
    - use_ai=True: Inherits from CrewAI Agent, can use LLM for complex tasks
    """

    def __init__(self, field_name: str, llm: Optional[Any] = None, use_ai: bool = False):
        """
        Initialize validator

        Args:
            field_name: Name of field being validated
            llm: Optional LLM instance (required if use_ai=True)
            use_ai: Whether this validator uses AI for validation
        """
        self.field_name = field_name
        self.use_ai = use_ai
        self.llm = llm

        # Only initialize as CrewAI Agent if we need AI capabilities
        if use_ai:
            if not llm:
                raise ValueError(f"{field_name}Validator requires llm when use_ai=True")

            # Initialize Agent parent class
            # Note: We can't use super().__init__() because we're not always inheriting from Agent
            # Instead, we manually set Agent attributes when needed
            self._init_as_agent(field_name, llm)
        else:
            # Just a regular Python class - no Agent overhead
            self.role = f'{field_name} Validator'
            self.goal = f'Validate {field_name} field'
            self.backstory = f'Expert validator for {field_name}'

    def _init_as_agent(self, field_name: str, llm: Any):
        """Initialize as CrewAI Agent (only called when use_ai=True)"""
        # Make this validator inherit Agent behavior dynamically
        # This is a bit of Python magic to avoid multiple inheritance issues
        self.__class__.__bases__ = (Agent,)

        Agent.__init__(
            self,
            role=f'{field_name} Validator',
            goal=f'Validate and improve {field_name} field according to LepSoc standards',
            backstory=f'Expert validator for {field_name} in Lepidopterist Society data, '
                     f'with deep knowledge of field standards and best practices',
            llm=llm,
            allow_delegation=False,
            verbose=False  # Set to True for debugging AI validators
        )

    def validate(self, value: Any, row_data: Optional[Dict] = None) -> ValidationResult:
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

    def execute_ai_task(self, description: str, context: str = "") -> str:
        """
        Execute an AI task using CrewAI

        Only works if use_ai=True and llm is provided.

        Args:
            description: Task description for the LLM
            context: Additional context to help the LLM

        Returns:
            str: LLM response
        """
        if not self.use_ai or not self.llm:
            raise RuntimeError(f"{self.field_name}Validator.execute_ai_task() "
                             f"requires use_ai=True and llm to be provided")

        task = Task(
            description=f"{context}\n\n{description}" if context else description,
            agent=self,
            expected_output="Validation result or suggestion"
        )

        # Execute via CrewAI
        result = self.execute_task(task)
        return str(result).strip()
