"""
Metadata field validators (Location, Name, Comments)
"""
from typing import Any, Dict
import pandas as pd
import re

from .base import BaseValidator
from ..models.validation_result import ValidationResult
from ..config import GPS_DECIMAL_PATTERN, GPS_DMS_PATTERN, COMMENT_STYLE_GUIDE, LEPIDOPTERIST_ABBREVIATIONS


# Location shortening guidelines for LLM
LOCATION_STYLE_GUIDE = """
LepSoc Specific Location Guidelines:

Format Rules:
- CRITICAL: Maximum 50 characters - count carefully!
- Use aggressive abbreviations to preserve key information
- Remove city/town names (already in County/State fields)
- Remove unnecessary words: "at", "the", "located at", "in the vicinity of", "intersection of"
- Keep essential identifiers: road names, landmarks, intersections
- Use slash notation for intersections: CR70/SH74
- Preserve GPS coordinates if present (decimal format preferred)
- NO ELLIPSIS (...) - use abbreviations to fit within 50 chars

Abbreviation Rules:
- Geographic: "Lake" → "Lk", "River" → "Rv", "Creek" → "Cr", "Mountain" → "Mt"
- Road types: "Road" → "Rd", "Highway" → "Hwy", "Trail" → "Tr"
- Road designations: "County Road" → "CR", "State Highway" → "SH", "State Route" → "SR"
- Directions: "near" → "nr", "north of" → "N of", "east" → "E", "west" → "W"
- Locations: "Campground" → "CG", "Site" → "S", "mile marker" → "mi"
- Distance: Remove spaces in measurements: "5 KM ESE" → "5KM ESE"

Examples (MUST be 50 characters or less):
- "Round Lake Road near Tuscarora Lodge at the intersection of County Road 70 and State Highway 74, 5 KM ESE of Fredricksburg" → "Round Lk Rd nr Tuscarora Lodge, 5KM ESE CR70/SH74"
- "Bob Richardson Campground Site 22" → "Bob Richardson CG S22"
- "near Plouff Creek County Park" → "nr Plouff Cr County Park"
- "North of Woodman Creek area" → "N of Woodman Cr"
- "Highway 61 at mile marker 15" → "Hwy 61 mi 15"

Key Principle: Maximize information density. Keep intersections and landmarks, remove redundant city names.
"""


class LocationValidator(BaseValidator):
    """Agent 11: Validate Specific Location field (Column K)

    Uses LLM to automatically shorten locations exceeding 50 characters
    according to lepidopterist location conventions.
    """

    def __init__(self, llm):
        super().__init__('Specific Location', llm=llm, requires="llm")

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

            # Use LLM to automatically shorten
            try:
                shortened = self.execute_ai_task(
                    description=f"Shorten this location to EXACTLY 50 characters or less. Use aggressive abbreviations. NO ELLIPSIS. Location: '{location}'",
                    context=LOCATION_STYLE_GUIDE
                ).strip()

                # Validate LLM output length
                if len(shortened) > 50:
                    # LLM failed to follow instructions - flag for manual review
                    result.warnings.append(f"LLM output too long ({len(shortened)} chars): {shortened}")
                    result.errors.append(f"Auto-shortening failed - needs manual review")
                    result.metadata['needs_manual_shortening'] = True
                else:
                    result.correction = shortened
                    result.correction_type = "correction"  # LLM shortening is a real correction
                    result.metadata['ai_shortened'] = True
            except Exception as e:
                result.errors.append(f"Could not automatically shorten location: {str(e)}")
                result.metadata['needs_manual_shortening'] = True

        return result


class NameValidator(BaseValidator):
    """Agent 14: Validate Name field (Column N)"""

    def __init__(self):
        super().__init__('Name')

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
    """Agent 15: Validate Comments field (Column O)

    Uses AI to shorten/standardize comments according to LepSoc style guidelines.
    """

    def __init__(self, llm):
        super().__init__('Comments', llm=llm, requires="llm")

    def validate(self, value: Any, row_data: Dict = None) -> ValidationResult:
        result = ValidationResult(self.field_name, value)

        # Optional field
        if pd.isna(value) or value == '':
            return result

        comments = str(value).strip()

        # Check for GPS coordinates (both decimal and DMS formats)
        has_decimal_gps = re.search(GPS_DECIMAL_PATTERN, comments)
        has_dms_gps = re.search(GPS_DMS_PATTERN, comments)

        if has_decimal_gps or has_dms_gps:
            result.metadata['has_gps_coords'] = True

        # If exceeds length, use AI to shorten
        if len(comments) > 120:
            result.warnings.append(f"Comments exceed 120 characters: {len(comments)}")

            # Use AI to shorten and standardize
            try:
                shortened = self.execute_ai_task(
                    description=f"Shorten this comment to max 120 characters: '{comments}'",
                    context=COMMENT_STYLE_GUIDE
                )
                result.correction = shortened
                result.correction_type = "correction"  # LLM shortening is a real correction
                result.metadata['ai_shortened'] = True
            except Exception as e:
                result.errors.append(f"Could not automatically shorten comment: {str(e)}")

        return result
