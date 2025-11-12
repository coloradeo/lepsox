"""
QA Agent for final validation checks across the entire dataset
"""
from typing import Dict, List, Any
import pandas as pd
from datetime import datetime


class RecordQAAgent:
    """Final QA pass to enforce cross-row validation rules

    Current responsibilities:
    1. State Record Uniqueness: Only one occurrence of each species can be marked as a state record
       - Choose the one with the earliest date
       - If dates are the same, choose the first in the file
    2. County Record Uniqueness: Only one occurrence of each species per county can be marked as a county record
       - Same logic as state records
    3. Hallucination Detection: Verify LLM-shortened fields don't contain invented information
       - Check Location and Comments fields for content not in original
       - Flag hallucinations as errors requiring manual review
    """

    def __init__(self):
        self.name = "RecordQAAgent"

    def validate_record_uniqueness(self, df: pd.DataFrame, validation_results: List[Dict]) -> List[Dict]:
        """
        Enforce state/county record uniqueness rules across the entire dataset.

        Args:
            df: DataFrame with validated data
            validation_results: List of validation results from individual row validations

        Returns:
            Updated validation_results with record uniqueness errors added
        """
        # Group by species (Family + Genus + Species + Subspecies)
        species_groups = self._group_by_species(df, validation_results)

        # Check state records
        self._validate_state_records(species_groups, df, validation_results)

        # Check county records (grouped by species + county)
        self._validate_county_records(species_groups, df, validation_results)

        return validation_results

    def _group_by_species(self, df: pd.DataFrame, validation_results: List[Dict]) -> Dict[str, List[int]]:
        """Group row indices by species identifier"""
        species_groups = {}

        for i, row in df.iterrows():
            # Build species key (Family + Genus + Species + Subspecies)
            family = str(row.get('Family', '')).strip()
            genus = str(row.get('Genus', '')).strip()
            species = str(row.get('Species', '')).strip()
            subspecies = str(row.get('Sub-species', '')).strip()

            # Skip if no species info
            if not family or not genus or not species:
                continue

            species_key = f"{family}|{genus}|{species}|{subspecies}"

            if species_key not in species_groups:
                species_groups[species_key] = []

            species_groups[species_key].append(i)

        return species_groups

    def _validate_state_records(self, species_groups: Dict[str, List[int]],
                                  df: pd.DataFrame, validation_results: List[Dict]):
        """Validate that only one occurrence of each species is marked as a state record"""

        for species_key, row_indices in species_groups.items():
            # Find all rows marked as state records for this species
            state_record_rows = []

            for idx in row_indices:
                state_record = str(df.iloc[idx].get('State Record', '')).strip().upper()
                if state_record in ['Y', 'YES', '1', 'TRUE']:
                    state_record_rows.append(idx)

            # If multiple state records exist, keep only the earliest
            if len(state_record_rows) > 1:
                # Sort by date (First Date), then by row index
                earliest_idx = self._find_earliest_record(df, state_record_rows)

                # Mark all others as errors
                for idx in state_record_rows:
                    if idx != earliest_idx:
                        result_idx = self._find_result_index(validation_results, idx)
                        if result_idx is not None:
                            validation_results[result_idx]['is_valid'] = False
                            validation_results[result_idx]['errors'].append(
                                f"State Record: Duplicate state record for species. "
                                f"Only row {earliest_idx + 1} (earliest date) should be marked as state record."
                            )

    def _validate_county_records(self, species_groups: Dict[str, List[int]],
                                   df: pd.DataFrame, validation_results: List[Dict]):
        """Validate that only one occurrence of each species per county is marked as a county record"""

        for species_key, row_indices in species_groups.items():
            # Group by county within this species
            county_groups = {}

            for idx in row_indices:
                county = str(df.iloc[idx].get('County', '')).strip()
                county_record = str(df.iloc[idx].get('County Record', '')).strip().upper()

                if county_record in ['Y', 'YES', '1', 'TRUE']:
                    if county not in county_groups:
                        county_groups[county] = []
                    county_groups[county].append(idx)

            # Check each county for duplicates
            for county, county_record_rows in county_groups.items():
                if len(county_record_rows) > 1:
                    # Sort by date (First Date), then by row index
                    earliest_idx = self._find_earliest_record(df, county_record_rows)

                    # Mark all others as errors
                    for idx in county_record_rows:
                        if idx != earliest_idx:
                            result_idx = self._find_result_index(validation_results, idx)
                            if result_idx is not None:
                                validation_results[result_idx]['is_valid'] = False
                                validation_results[result_idx]['errors'].append(
                                    f"County Record: Duplicate county record for species in {county}. "
                                    f"Only row {earliest_idx + 1} (earliest date) should be marked as county record."
                                )

    def _find_earliest_record(self, df: pd.DataFrame, row_indices: List[int]) -> int:
        """Find the row with the earliest date, or first in file if dates are the same"""

        def parse_date(date_str):
            """Parse LepSoc date format (DD-MMM-YY) to datetime"""
            try:
                date_str = str(date_str).strip()
                if not date_str or date_str == 'nan':
                    return None
                # Handle DD-MMM-YY format (e.g., "15-JUN-23")
                return datetime.strptime(date_str, "%d-%b-%y")
            except:
                return None

        # Create list of (index, date, row_position)
        date_list = []
        for i, idx in enumerate(row_indices):
            first_date = df.iloc[idx].get('First Date', '')
            parsed_date = parse_date(first_date)
            date_list.append((idx, parsed_date, i))

        # Sort by: date (None last), then by original row position
        date_list.sort(key=lambda x: (x[1] is None, x[1] if x[1] else datetime.max, x[2]))

        return date_list[0][0]  # Return the earliest row index

    def _find_result_index(self, validation_results: List[Dict], row_idx: int) -> int:
        """Find the validation result index for a given row index"""
        for i, result in enumerate(validation_results):
            if result.get('row_index') == row_idx:
                return i
        return None

    def validate_hallucinations(self, df: pd.DataFrame, validation_results: List[Dict]) -> List[Dict]:
        """
        Detect hallucinations in LLM-shortened fields by checking if shortened text
        contains words/tokens not present in the original text.

        Checks 'Specific Location' and 'Comments' fields that have ai_shortened metadata.

        Args:
            df: DataFrame with validated data
            validation_results: List of validation results from individual row validations

        Returns:
            Updated validation_results with hallucination errors added
        """
        import re

        def extract_tokens(text):
            """Extract alphanumeric tokens from text (words, numbers, abbreviations)"""
            text = str(text).upper()
            # Extract words and numbers, including abbreviations like CR70, SH74
            tokens = set(re.findall(r'\b[A-Z0-9]+\b', text))
            return tokens

        # Check each row
        for i, result in enumerate(validation_results):
            row_idx = result.get('row_index')
            if row_idx is None:
                continue

            # Check Specific Location field
            if 'Specific Location' in result.get('corrections', {}):
                field_result = result.get('field_results', {}).get('Specific Location')

                # Only check if it was AI-shortened
                if field_result and field_result.metadata.get('ai_shortened'):
                    original = str(df.iloc[i].get('Specific Location', '')).strip()
                    shortened = result['corrections']['Specific Location']

                    # Extract tokens from both
                    original_tokens = extract_tokens(original)
                    shortened_tokens = extract_tokens(shortened)

                    # Find tokens in shortened that aren't in original
                    hallucinated_tokens = shortened_tokens - original_tokens

                    # Filter out common abbreviations that are valid transformations
                    valid_abbreviations = {
                        'LK', 'RV', 'CR', 'MT', 'RD', 'HWY', 'TR', 'SH', 'SR',
                        'NR', 'N', 'S', 'E', 'W', 'CAMPGD', 'MI', 'KM',
                        'ESE', 'WSW', 'NNE', 'SSW', 'NW', 'NE', 'SE', 'SW'
                    }
                    hallucinated_tokens = hallucinated_tokens - valid_abbreviations

                    if hallucinated_tokens:
                        result['is_valid'] = False
                        result['errors'].append(
                            f"Specific Location: LLM hallucination detected - added content not in original: {', '.join(sorted(hallucinated_tokens))}"
                        )
                        result['metadata']['hallucination_detected'] = True
                        # Remove the correction so original is kept
                        del result['corrections']['Specific Location']

            # Check Comments field
            if 'Comments' in result.get('corrections', {}):
                field_result = result.get('field_results', {}).get('Comments')

                # Only check if it was AI-shortened
                if field_result and field_result.metadata.get('ai_shortened'):
                    original = str(df.iloc[i].get('Comments', '')).strip()
                    shortened = result['corrections']['Comments']

                    # Extract tokens from both
                    original_tokens = extract_tokens(original)
                    shortened_tokens = extract_tokens(shortened)

                    # Find tokens in shortened that aren't in original
                    hallucinated_tokens = shortened_tokens - original_tokens

                    # Filter out common abbreviations
                    valid_abbreviations = {
                        'LK', 'RV', 'CR', 'MT', 'RD', 'HWY', 'TR', 'SH', 'SR',
                        'NR', 'N', 'S', 'E', 'W', 'CAMPGD', 'MI', 'KM',
                        'LT', 'MV', 'UV', 'NECT', 'OVIPOS', 'BASK'
                    }
                    hallucinated_tokens = hallucinated_tokens - valid_abbreviations

                    if hallucinated_tokens:
                        result['is_valid'] = False
                        result['errors'].append(
                            f"Comments: LLM hallucination detected - added content not in original: {', '.join(sorted(hallucinated_tokens))}"
                        )
                        result['metadata']['hallucination_detected'] = True
                        # Remove the correction so original is kept
                        del result['corrections']['Comments']

        return validation_results
