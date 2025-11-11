"""
Main validation orchestrator using CrewAI
"""
from typing import Dict, List, Any
import pandas as pd
from crewai import Crew, Task, Process
from langchain.llms import Ollama

from .config import OLLAMA_BASE_URL, OLLAMA_MODEL, COLUMN_NAMES
from .agents import (
    ZoneValidator, CountryValidator, StateValidator, CountyValidator,
    FamilyValidator, GenusValidator, SpeciesValidator, SubspeciesValidator,
    FirstDateValidator, LastDateValidator, YearValidator,
    StateRecordValidator, CountyRecordValidator,
    LocationValidator, NameValidator, CommentValidator
)


class LepSocValidationCrew:
    """Main CrewAI orchestrator for validation"""

    def __init__(self, ollama_url: str = OLLAMA_BASE_URL, ollama_model: str = OLLAMA_MODEL):
        # Initialize Ollama LLM
        self.llm = Ollama(
            model=ollama_model,
            base_url=ollama_url
        )

        # Create all validation agents
        self.validators = self._create_validators()

        # Column mapping
        self.column_names = COLUMN_NAMES

    def _create_validators(self) -> List:
        """Create all 16 validation agents"""
        validators = [
            ZoneValidator(self.llm),
            CountryValidator(self.llm),
            StateValidator(self.llm),
            FamilyValidator(self.llm),
            GenusValidator(self.llm),
            SpeciesValidator(self.llm),
            SubspeciesValidator(self.llm),
            CountyValidator(self.llm),
            StateRecordValidator(self.llm),
            CountyRecordValidator(self.llm),
            LocationValidator(self.llm),
            FirstDateValidator(self.llm),
            LastDateValidator(self.llm),
            NameValidator(self.llm),
            CommentValidator(self.llm),
            YearValidator(self.llm)
        ]
        return validators

    def validate_row(self, row_index: int, row_data: pd.Series) -> Dict[str, Any]:
        """
        Validate a single row using all agents

        Args:
            row_index: Row index in the dataframe
            row_data: Pandas Series containing row data

        Returns:
            Dict containing validation results
        """
        # Convert row to dict for easier access
        row_dict = row_data.to_dict()

        # Results container
        validation_results = {
            'row_index': row_index,
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'corrections': {},
            'metadata': {},
            'needs_review': False
        }

        # Create tasks for each field
        tasks = []
        for i, (col_name, validator) in enumerate(zip(self.column_names, self.validators)):
            value = row_data.iloc[i] if i < len(row_data) else None

            # Create validation task
            task = Task(
                description=f'Validate {col_name} field with value: {value}',
                agent=validator,
                expected_output='Validation result with any errors or corrections'
            )
            tasks.append(task)

        # Create and run crew (simple sequential processing for now)
        try:
            # Run validators directly
            for i, (col_name, validator) in enumerate(zip(self.column_names, self.validators)):
                value = row_data.iloc[i] if i < len(row_data) else None

                # Run validation
                result = validator.validate(value, row_dict)

                # Process results
                if not result.is_valid:
                    validation_results['is_valid'] = False
                    validation_results['errors'].extend(
                        [f"{col_name}: {e}" for e in result.errors]
                    )

                if result.warnings:
                    validation_results['warnings'].extend(
                        [f"{col_name}: {w}" for w in result.warnings]
                    )

                if result.correction is not None:
                    validation_results['corrections'][col_name] = result.correction

                if result.metadata:
                    validation_results['metadata'][col_name] = result.metadata

                # Check if review needed
                if result.metadata.get('needs_inat_check') or \
                   result.metadata.get('needs_inat_verification'):
                    validation_results['needs_review'] = True

        except Exception as e:
            validation_results['is_valid'] = False
            validation_results['errors'].append(f"Validation error: {str(e)}")

        return validation_results

    def validate_file(self, filepath: str, output_path: str = None) -> pd.DataFrame:
        """
        Validate entire Excel/CSV file

        Args:
            filepath: Path to input file
            output_path: Optional path for output file

        Returns:
            DataFrame with validation results
        """
        # Read file
        if filepath.endswith('.xlsx'):
            df = pd.read_excel(filepath, header=None)
        else:
            df = pd.read_csv(filepath, header=None)

        # Ensure we have 16 columns
        if len(df.columns) < 16:
            raise ValueError(f"File must have 16 columns, found {len(df.columns)}")

        # Rename columns
        df.columns = self.column_names[:len(df.columns)]

        # Validation results
        all_results = []

        print(f"Validating {len(df)} rows...")

        # Process each row
        for index, row in df.iterrows():
            print(f"\nValidating row {index + 1}/{len(df)}")
            result = self.validate_row(index, row)
            all_results.append(result)

            # Show results
            if result['errors']:
                print(f"  ✗ Errors: {', '.join(result['errors'][:3])}")
            if result['warnings']:
                print(f"  ⚠ Warnings: {', '.join(result['warnings'][:3])}")
            if result['corrections']:
                print(f"  ✓ Corrections: {len(result['corrections'])} fields")

        # Apply corrections and add metadata columns
        validated_df = self._apply_corrections(df, all_results)

        # Save output
        if output_path:
            if output_path.endswith('.xlsx'):
                validated_df.to_excel(output_path, index=False)
            else:
                validated_df.to_csv(output_path, index=False)
            print(f"\n✓ Validated file saved to: {output_path}")

        # Summary
        self._print_summary(all_results)

        return validated_df

    def _apply_corrections(self, df: pd.DataFrame, results: List[Dict]) -> pd.DataFrame:
        """Apply corrections and add metadata columns"""
        validated_df = df.copy()

        # Add metadata columns
        validated_df['Validation_Status'] = ''
        validated_df['Validation_Notes'] = ''
        validated_df['Original_Values'] = ''
        validated_df['Confidence_Score'] = ''
        validated_df['Validated_By'] = ''

        for i, result in enumerate(results):
            # Set validation status
            if result['is_valid'] and not result['corrections']:
                validated_df.loc[i, 'Validation_Status'] = 'PASS'
            elif result['corrections']:
                validated_df.loc[i, 'Validation_Status'] = 'CORRECTED'
            else:
                validated_df.loc[i, 'Validation_Status'] = 'FAIL'

            # Apply corrections
            original_values = []
            for field, correction in result['corrections'].items():
                if field in validated_df.columns:
                    original = validated_df.loc[i, field]
                    if str(original) != str(correction):
                        original_values.append(f"{field}: {original}")
                        validated_df.loc[i, field] = correction

            # Set metadata
            if result['errors']:
                validated_df.loc[i, 'Validation_Notes'] = '; '.join(result['errors'][:3])
            elif result['warnings']:
                validated_df.loc[i, 'Validation_Notes'] = '; '.join(result['warnings'][:3])

            if original_values:
                validated_df.loc[i, 'Original_Values'] = '; '.join(original_values)

            validated_df.loc[i, 'Validated_By'] = 'CrewAI Agent'

            # Set confidence based on status
            if result['is_valid'] and not result['corrections']:
                validated_df.loc[i, 'Confidence_Score'] = '1.0'
            elif result['corrections']:
                validated_df.loc[i, 'Confidence_Score'] = '0.8'
            else:
                validated_df.loc[i, 'Confidence_Score'] = '0.5'

        return validated_df

    def _print_summary(self, results: List[Dict]):
        """Print validation summary"""
        total = len(results)
        passed = sum(1 for r in results if r['is_valid'] and not r['corrections'])
        corrected = sum(1 for r in results if r['corrections'])
        failed = sum(1 for r in results if not r['is_valid'])
        needs_review = sum(1 for r in results if r['needs_review'])

        print("\n" + "="*50)
        print("VALIDATION SUMMARY")
        print("="*50)
        print(f"Total Rows: {total}")
        print(f"✓ Passed: {passed} ({passed/total*100:.1f}%)")
        print(f"✓ Corrected: {corrected} ({corrected/total*100:.1f}%)")
        print(f"✗ Failed: {failed} ({failed/total*100:.1f}%)")
        print(f"? Needs Review: {needs_review} ({needs_review/total*100:.1f}%)")
        print("="*50)
