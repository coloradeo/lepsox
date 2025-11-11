"""
LepSoc Season Summary Validation System
Simple CrewAI Implementation
"""

from crewai import Agent, Crew, Task, Process
from langchain.llms import Ollama
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from datetime import datetime
import re
import json
import asyncio
from mcp import ClientSession
from mcp.client.sse import sse_client

# Configuration
OLLAMA_BASE_URL = "http://192.168.51.99:30068"
OLLAMA_MODEL = "llama2"
INAT_MCP_URL = "http://192.168.51.99:8811/sse"

# Valid values for validation
VALID_ZONES = list(range(1, 13))  # 1-12
VALID_COUNTRIES = ["USA", "CAN", "MEX"]
DATE_FORMAT = r'^\d{1,2}-[A-Z]{3}-\d{2}$'

# US State abbreviations
US_STATES = [
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY", "DC"
]

# Canadian provinces
CAN_PROVINCES = [
    "AB", "BC", "MB", "NB", "NL", "NS", "NT", "NU", "ON", "PE", "QC", "SK", "YT"
]

# Mexican states (abbreviated)
MEX_STATES = [
    "AGU", "BCN", "BCS", "CAM", "CHP", "CHH", "COA", "COL", "CMX", "DUR",
    "GUA", "GRO", "HID", "JAL", "MEX", "MIC", "MOR", "NAY", "NLE", "OAX",
    "PUE", "QUE", "ROO", "SLP", "SIN", "SON", "TAB", "TAM", "TLA", "VER", "YUC", "ZAC"
]


class ValidationResult:
    """Container for validation results"""
    def __init__(self, field_name: str, value: Any):
        self.field_name = field_name
        self.value = value
        self.is_valid = True
        self.errors = []
        self.warnings = []
        self.correction = None
        self.metadata = {}
    
    def to_dict(self):
        return {
            'field': self.field_name,
            'value': self.value,
            'is_valid': self.is_valid,
            'errors': self.errors,
            'warnings': self.warnings,
            'correction': self.correction,
            'metadata': self.metadata
        }


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
        """Override in subclasses"""
        result = ValidationResult(self.field_name, value)
        return result


class ZoneValidator(BaseValidator):
    """Agent 1: Validate Zone field (Column A)"""
    
    def __init__(self, llm):
        super().__init__('Zone', llm)
    
    def validate(self, value: Any, row_data: Dict = None) -> ValidationResult:
        result = ValidationResult(self.field_name, value)
        
        # Check if value exists
        if pd.isna(value) or value == '':
            result.is_valid = False
            result.errors.append("Zone is required")
            return result
        
        # Convert to int and validate range
        try:
            zone_num = int(value)
            if zone_num not in VALID_ZONES:
                result.is_valid = False
                result.errors.append(f"Zone must be between 1-12, got {zone_num}")
            else:
                result.correction = str(zone_num)  # Ensure string format
        except (ValueError, TypeError):
            result.is_valid = False
            result.errors.append(f"Zone must be numeric, got {value}")
        
        return result


class CountryValidator(BaseValidator):
    """Agent 2: Validate Country field (Column B)"""
    
    def __init__(self, llm):
        super().__init__('Country', llm)
    
    def validate(self, value: Any, row_data: Dict = None) -> ValidationResult:
        result = ValidationResult(self.field_name, value)
        
        if pd.isna(value) or value == '':
            result.is_valid = False
            result.errors.append("Country is required")
            return result
        
        value_upper = str(value).upper().strip()
        
        if value_upper not in VALID_COUNTRIES:
            result.is_valid = False
            result.errors.append(f"Country must be USA, CAN, or MEX, got {value}")
        
        if len(value_upper) != 3:
            result.is_valid = False
            result.errors.append(f"Country must be exactly 3 characters")
        
        result.correction = value_upper
        return result


class StateValidator(BaseValidator):
    """Agent 3: Validate State/Province field (Column C)"""
    
    def __init__(self, llm):
        super().__init__('State', llm)
    
    def validate(self, value: Any, row_data: Dict = None) -> ValidationResult:
        result = ValidationResult(self.field_name, value)
        
        if pd.isna(value) or value == '':
            result.is_valid = False
            result.errors.append("State/Province is required")
            return result
        
        state = str(value).upper().strip()
        country = row_data.get('Country', '').upper() if row_data else ''
        
        # Validate based on country
        if country == 'USA':
            if state not in US_STATES:
                result.is_valid = False
                result.errors.append(f"Invalid US state: {state}")
        elif country == 'CAN':
            if state not in CAN_PROVINCES:
                result.is_valid = False
                result.errors.append(f"Invalid Canadian province: {state}")
        elif country == 'MEX':
            if state not in MEX_STATES:
                result.warnings.append(f"Please verify Mexican state code: {state}")
        
        if len(state) > 3:
            result.is_valid = False
            result.errors.append("State/Province must be 3 characters or less")
        
        result.correction = state
        return result


class FamilyValidator(BaseValidator):
    """Agent 4: Validate Family field (Column D)"""
    
    def __init__(self, llm):
        super().__init__('Family', llm)
        self.valid_families = [
            'Hesperiidae', 'Papilionidae', 'Pieridae', 'Lycaenidae',
            'Riodinidae', 'Nymphalidae', 'Geometridae', 'Erebidae',
            'Noctuidae', 'Notodontidae', 'Sphingidae', 'Saturniidae',
            'Lasiocampidae', 'Megalopygidae', 'Limacodidae', 'Crambidae',
            'Pyralidae', 'Tortricidae', 'Cossidae', 'Sesiidae'
        ]
    
    def validate(self, value: Any, row_data: Dict = None) -> ValidationResult:
        result = ValidationResult(self.field_name, value)
        
        if pd.isna(value) or value == '':
            result.is_valid = False
            result.errors.append("Family is required")
            return result
        
        family = str(value).strip()
        
        # Check length
        if len(family) > 20:
            result.is_valid = False
            result.errors.append(f"Family exceeds 20 characters: {len(family)}")
        
        # Check if it's a known Lepidoptera family
        if family not in self.valid_families:
            result.warnings.append(f"Uncommon family name: {family}. Please verify.")
            result.metadata['needs_inat_check'] = True
        
        return result


class GenusValidator(BaseValidator):
    """Agent 5: Validate Genus field (Column E)"""
    
    def __init__(self, llm):
        super().__init__('Genus', llm)
    
    def validate(self, value: Any, row_data: Dict = None) -> ValidationResult:
        result = ValidationResult(self.field_name, value)
        
        if pd.isna(value) or value == '':
            result.is_valid = False
            result.errors.append("Genus is required")
            return result
        
        genus = str(value).strip()
        
        # Check length
        if len(genus) > 20:
            result.is_valid = False
            result.errors.append(f"Genus exceeds 20 characters: {len(genus)}")
        
        # Check capitalization
        if genus and not genus[0].isupper():
            result.warnings.append("Genus should start with capital letter")
            result.correction = genus.capitalize()
        
        result.metadata['needs_inat_check'] = True
        return result


class SpeciesValidator(BaseValidator):
    """Agent 6: Validate Species field (Column F)"""
    
    def __init__(self, llm):
        super().__init__('Species', llm)
    
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
        
        result.metadata['needs_inat_check'] = True
        return result


class SubspeciesValidator(BaseValidator):
    """Agent 7: Validate Sub-species field (Column G)"""
    
    def __init__(self, llm):
        super().__init__('Sub-species', llm)
    
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
        
        return result


class CountyValidator(BaseValidator):
    """Agent 8: Validate County field (Column H)"""
    
    def __init__(self, llm):
        super().__init__('County', llm)
    
    def validate(self, value: Any, row_data: Dict = None) -> ValidationResult:
        result = ValidationResult(self.field_name, value)
        
        if pd.isna(value) or value == '':
            result.is_valid = False
            result.errors.append("County is required")
            return result
        
        county = str(value).strip()
        
        # Check length
        if len(county) > 20:
            result.is_valid = False
            result.errors.append(f"County exceeds 20 characters: {len(county)}")
        
        # Should not include "County" suffix
        if 'County' in county or 'Province' in county or 'Territory' in county:
            result.warnings.append("Remove 'County/Province/Territory' from name")
            county_cleaned = county.replace('County', '').replace('Province', '').replace('Territory', '').strip()
            result.correction = county_cleaned
        
        result.metadata['needs_inat_check'] = True
        return result


class StateRecordValidator(BaseValidator):
    """Agent 9: Validate State Record field (Column I)"""
    
    def __init__(self, llm):
        super().__init__('State Record', llm)
    
    def validate(self, value: Any, row_data: Dict = None) -> ValidationResult:
        result = ValidationResult(self.field_name, value)
        
        # Optional field
        if pd.isna(value) or value == '':
            return result
        
        value_upper = str(value).upper().strip()
        
        if value_upper not in ['Y', 'N']:
            result.is_valid = False
            result.errors.append("State Record must be Y, N, or blank")
        
        result.correction = value_upper
        result.metadata['needs_inat_verification'] = True
        return result


class CountyRecordValidator(BaseValidator):
    """Agent 10: Validate County Record field (Column J)"""
    
    def __init__(self, llm):
        super().__init__('County Record', llm)
    
    def validate(self, value: Any, row_data: Dict = None) -> ValidationResult:
        result = ValidationResult(self.field_name, value)
        
        # Optional field
        if pd.isna(value) or value == '':
            return result
        
        value_upper = str(value).upper().strip()
        
        if value_upper not in ['Y', 'N']:
            result.is_valid = False
            result.errors.append("County Record must be Y, N, or blank")
        
        result.correction = value_upper
        result.metadata['needs_inat_verification'] = True
        return result


class LocationValidator(BaseValidator):
    """Agent 11: Validate Specific Location field (Column K)"""
    
    def __init__(self, llm):
        super().__init__('Specific Location', llm)
    
    def validate(self, value: Any, row_data: Dict = None) -> ValidationResult:
        result = ValidationResult(self.field_name, value)
        
        if pd.isna(value) or value == '':
            result.is_valid = False
            result.errors.append("Specific Location is required")
            return result
        
        location = str(value).strip()
        
        if len(location) > 50:
            result.is_valid = False
            result.errors.append(f"Location exceeds 50 characters: {len(location)}")
            result.metadata['overflow_to_comments'] = location[50:]
        
        return result


class FirstDateValidator(BaseValidator):
    """Agent 12: Validate First Date field (Column L)"""
    
    def __init__(self, llm):
        super().__init__('First Date', llm)
    
    def validate(self, value: Any, row_data: Dict = None) -> ValidationResult:
        result = ValidationResult(self.field_name, value)
        
        if pd.isna(value) or value == '':
            result.is_valid = False
            result.errors.append("First Date is required")
            return result
        
        date_str = str(value).strip()
        
        # Check format dd-mmm-yy
        if not re.match(DATE_FORMAT, date_str.upper()):
            result.is_valid = False
            result.errors.append(f"Date format must be dd-mmm-yy, got {date_str}")
        
        # Check if date is reasonable (within last 3 years)
        try:
            # Parse date
            date_parts = date_str.split('-')
            if len(date_parts) == 3:
                year = int(date_parts[2])
                # Convert 2-digit year to 4-digit
                if year < 100:
                    year = 2000 + year if year < 50 else 1900 + year
                
                current_year = datetime.now().year
                if current_year - year > 3:
                    result.warnings.append(f"Date is more than 3 years old: {year}")
        except:
            pass
        
        return result


class LastDateValidator(BaseValidator):
    """Agent 13: Validate Last Date field (Column M)"""
    
    def __init__(self, llm):
        super().__init__('Last Date', llm)
    
    def validate(self, value: Any, row_data: Dict = None) -> ValidationResult:
        result = ValidationResult(self.field_name, value)
        
        # Optional field
        if pd.isna(value) or value == '':
            return result
        
        date_str = str(value).strip()
        
        # Check format
        if not re.match(DATE_FORMAT, date_str.upper()):
            result.is_valid = False
            result.errors.append(f"Date format must be dd-mmm-yy, got {date_str}")
        
        # TODO: Compare with First Date to ensure Last >= First
        
        return result


class NameValidator(BaseValidator):
    """Agent 14: Validate Name field (Column N)"""
    
    def __init__(self, llm):
        super().__init__('Name', llm)
    
    def validate(self, value: Any, row_data: Dict = None) -> ValidationResult:
        result = ValidationResult(self.field_name, value)
        
        # Optional field
        if pd.isna(value) or value == '':
            return result
        
        name_code = str(value).strip()
        
        if len(name_code) > 3:
            result.is_valid = False
            result.errors.append(f"Name code must be 3 characters or less")
        
        # TODO: Check against contributor codes master file
        result.metadata['needs_contributor_check'] = True
        
        return result


class CommentValidator(BaseValidator):
    """Agent 15: Validate Comments field (Column O)"""
    
    def __init__(self, llm):
        super().__init__('Comments', llm)
    
    def validate(self, value: Any, row_data: Dict = None) -> ValidationResult:
        result = ValidationResult(self.field_name, value)
        
        # Optional field
        if pd.isna(value) or value == '':
            return result
        
        comments = str(value).strip()
        
        if len(comments) > 120:
            result.is_valid = False
            result.errors.append(f"Comments exceed 120 characters: {len(comments)}")
        
        # Check for GPS coordinates pattern
        gps_pattern = r'[-+]?\d+\.?\d*,\s*[-+]?\d+\.?\d*'
        if re.search(gps_pattern, comments):
            result.metadata['has_gps_coords'] = True
        
        return result


class YearValidator(BaseValidator):
    """Agent 16: Validate Year field (Column P)"""
    
    def __init__(self, llm):
        super().__init__('Year', llm)
    
    def validate(self, value: Any, row_data: Dict = None) -> ValidationResult:
        result = ValidationResult(self.field_name, value)
        
        if pd.isna(value) or value == '':
            result.is_valid = False
            result.errors.append("Year is required")
            return result
        
        try:
            year = int(value)
            
            if year < 1000 or year > 9999:
                result.is_valid = False
                result.errors.append(f"Year must be 4 digits")
            
            current_year = datetime.now().year
            if current_year - year > 3:
                result.warnings.append(f"Year is more than 3 years old: {year}")
            
            if year > current_year:
                result.is_valid = False
                result.errors.append(f"Year cannot be in the future: {year}")
            
        except (ValueError, TypeError):
            result.is_valid = False
            result.errors.append(f"Year must be numeric: {value}")
        
        return result


class LepSocValidationCrew:
    """Main CrewAI orchestrator for validation"""
    
    def __init__(self):
        # Initialize Ollama LLM
        self.llm = Ollama(
            model=OLLAMA_MODEL,
            base_url=OLLAMA_BASE_URL
        )
        
        # Create all validation agents
        self.validators = self._create_validators()
        
        # Column mapping
        self.column_names = [
            'Zone', 'Country', 'State', 'Family', 'Genus', 'Species',
            'Sub-species', 'County', 'State Record', 'County Record',
            'Specific Location', 'First Date', 'Last Date', 'Name',
            'Comments', 'Year'
        ]
    
    def _create_validators(self) -> List[BaseValidator]:
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
        """Validate a single row using all agents"""
        
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
        
        # Create and run crew
        crew = Crew(
            agents=self.validators,
            tasks=tasks,
            process=Process.sequential,  # Run validators in sequence
            verbose=True
        )
        
        # Execute validation
        try:
            # For now, run validators directly (CrewAI kickoff can be async)
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
        """Validate entire Excel/CSV file"""
        
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
                print(f"  ❌ Errors: {', '.join(result['errors'][:3])}")
            if result['warnings']:
                print(f"  ⚠️  Warnings: {', '.join(result['warnings'][:3])}")
            if result['corrections']:
                print(f"  ✏️  Corrections: {len(result['corrections'])} fields")
        
        # Apply corrections and add metadata columns
        validated_df = self._apply_corrections(df, all_results)
        
        # Save output
        if output_path:
            if output_path.endswith('.xlsx'):
                validated_df.to_excel(output_path, index=False)
            else:
                validated_df.to_csv(output_path, index=False)
            print(f"\n✅ Validated file saved to: {output_path}")
        
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
        print(f"✅ Passed: {passed} ({passed/total*100:.1f}%)")
        print(f"✏️  Corrected: {corrected} ({corrected/total*100:.1f}%)")
        print(f"❌ Failed: {failed} ({failed/total*100:.1f}%)")
        print(f"🔍 Needs Review: {needs_review} ({needs_review/total*100:.1f}%)")
        print("="*50)


# Async iNaturalist integration
class INatValidator:
    """iNaturalist API integration for species/location validation"""
    
    def __init__(self):
        self.server_url = INAT_MCP_URL
    
    async def check_species(self, genus: str, species: str, family: str = None):
        """Validate species against iNaturalist"""
        async with sse_client(self.server_url) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # Search for species
                full_name = f"{genus} {species}"
                result = await session.call_tool("search_species", {
                    "query": full_name,
                    "limit": 3
                })
                
                if result.get('results'):
                    # Check if any result matches
                    for taxon in result['results']:
                        if genus.lower() in taxon.get('name', '').lower():
                            return {
                                'valid': True,
                                'taxon_id': taxon['taxon_id'],
                                'correct_name': taxon['name'],
                                'common_name': taxon.get('preferred_common_name', '')
                            }
                
                return {'valid': False, 'error': 'Species not found'}
    
    async def check_location(self, county: str, state: str, country: str):
        """Validate location against iNaturalist"""
        async with sse_client(self.server_url) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # Search for place
                place_query = f"{county}, {state}, {country}"
                result = await session.call_tool("search_places", {
                    "query": place_query,
                    "limit": 5
                })
                
                if result.get('results'):
                    return {
                        'valid': True,
                        'place_id': result['results'][0]['id'],
                        'display_name': result['results'][0]['display_name']
                    }
                
                return {'valid': False, 'error': 'Location not found'}
    
    async def check_record_status(self, taxon_id: int, place_id: int = None, 
                                  state: str = None, county: str = None):
        """Check if observation is a state or county record"""
        async with sse_client(self.server_url) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # Build place name
                if place_id:
                    place_param = {"place_id": place_id}
                elif county and state:
                    place_param = {"place_name": f"{county}, {state}"}
                elif state:
                    place_param = {"place_name": state}
                else:
                    return {'error': 'No location specified'}
                
                # Count existing observations
                result = await session.call_tool("count_observations", {
                    "taxon_id": taxon_id,
                    **place_param,
                    "quality_grade": "research"
                })
                
                # If no observations, it's a new record
                total = result.get('total_results', 0)
                return {
                    'is_new_record': total == 0,
                    'existing_count': total,
                    'query_url': result.get('query_url', '')
                }


def main():
    """Main execution function"""
    import sys
    
    print("LepSoc Season Summary Validation System")
    print("=" * 50)
    
    # Check command line arguments
    if len(sys.argv) < 2:
        print("Usage: python lepsoc_validator.py <input_file> [output_file]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else input_file.replace('.', '_validated.')
    
    # Create validation crew
    print(f"\nInitializing validation crew...")
    crew = LepSocValidationCrew()
    
    # Run validation
    print(f"Processing file: {input_file}")
    validated_df = crew.validate_file(input_file, output_file)
    
    print(f"\n✅ Validation complete!")
    print(f"Output saved to: {output_file}")


if __name__ == "__main__":
    main()
