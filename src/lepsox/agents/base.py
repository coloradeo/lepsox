"""
Base validator class for all field validators

Supports deterministic (pure Python), LLM-powered, and iNat-powered validation.
"""
from typing import Any, Dict, Optional, Literal
from crewai import Agent, Task

from ..models.validation_result import ValidationResult


class BaseValidator:
    """
    Base class for all validation agents

    Supports three validation modes:
    - requires=None: Simple Python logic, fast, no external services
    - requires="llm": Uses Ollama LLM via CrewAI for complex reasoning
    - requires="inat": Uses iNaturalist MCP for species/location validation
    """

    def __init__(self, field_name: str, llm: Optional[Any] = None,
                 requires: Optional[Literal["llm", "inat"]] = None):
        """
        Initialize validator

        Args:
            field_name: Name of field being validated
            llm: Optional LLM instance (required if requires="llm")
            requires: External service requirement - "llm" for Ollama, "inat" for iNat MCP, None for deterministic
        """
        self.field_name = field_name
        self.requires = requires
        self.llm = llm
        self._agent = None  # Composition: hold Agent instance

        # Only initialize CrewAI Agent if we need LLM capabilities
        if requires == "llm":
            if not llm:
                raise ValueError(f"{field_name}Validator requires llm when requires='llm'")

            # Create Agent instance (composition, not inheritance)
            self._agent = Agent(
                role=f'{field_name} Validator',
                goal=f'Validate and improve {field_name} field according to LepSoc standards',
                backstory=f'Expert validator for {field_name} in Lepidopterist Society data, '
                         f'with deep knowledge of field standards and best practices',
                llm=llm,
                allow_delegation=False,
                verbose=False  # Set to True for debugging AI validators
            )

            # Set these for compatibility
            self.role = self._agent.role
            self.goal = self._agent.goal
            self.backstory = self._agent.backstory
        else:
            # Just a regular Python class - no Agent overhead
            self.role = f'{field_name} Validator'
            self.goal = f'Validate {field_name} field'
            self.backstory = f'Expert validator for {field_name}'

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

        Only works if requires="llm" and llm is provided.

        Args:
            description: Task description for the LLM
            context: Additional context to help the LLM

        Returns:
            str: LLM response
        """
        if self.requires != "llm" or not self._agent:
            raise RuntimeError(f"{self.field_name}Validator.execute_ai_task() "
                             f"requires requires='llm' and llm to be provided")

        task = Task(
            description=f"{context}\n\n{description}" if context else description,
            agent=self._agent,
            expected_output="Validation result or suggestion"
        )

        # Execute via CrewAI Agent
        result = self._agent.execute_task(task)
        return str(result).strip()
