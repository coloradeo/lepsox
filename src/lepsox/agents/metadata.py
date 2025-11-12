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

GOAL: Someone must be able to find this exact location decades from now.

Priority Order (keep higher priority items when making tradeoffs):
1. PERMANENT LANDMARKS (MUST include):
   - Geographic features: lakes, rivers, creeks, mountains, ridges
   - Major road intersections: CR70/SH74, Hwy 61/CR 5
   - GPS coordinates (if present)
   - Mile markers on major roads
2. SEMI-PERMANENT (keep if space allows):
   - Named roads and trails (these persist for decades)
   - Public parks and natural areas
   - City/town names (helpful context, keep if room permits)
3. TEMPORARY (remove first when space is tight):
   - Business names: lodges, campgrounds, stores (remove these first)
   - Campground/trail site numbers (can change)

NOTE: City names provide useful context - keep them if you can fit within 50 chars after including permanent landmarks.

Format Rules:
- CRITICAL: Maximum 50 characters - count carefully!
- CRITICAL: NO HALLUCINATIONS - Use ONLY information from the original location text
- NEVER add intersections, road numbers, or details not present in the original
- If information is unclear or missing, omit it rather than guessing
- FIRST: Include all permanent landmarks with abbreviations
- THEN: If space remains, add city/town names for context
- Remove filler words: "at", "the", "located at", "in the vicinity of", "intersection of"
- Use slash notation for intersections: CR70/SH74 (ONLY if both roads are in original)
- NO ELLIPSIS (...) - abbreviate instead
- Use remaining space wisely - add helpful context if under 50 chars

CONTEXT AWARENESS - CRITICAL:
- Use context clues to identify proper names vs descriptive words
- "Big Lake Campground Rd" is a ROAD NAME - abbreviate to "Big Lk Campgd Rd", don't drop "Campground"
- "Big Lake" vs "Big Lake Campground" are DIFFERENT places - keep the full proper name
- If removing a word changes the meaning or makes it a different place, DON'T remove it
- Proper names must stay intact (with abbreviations) - only remove generic descriptors

Abbreviation Rules:
- Geographic: "Lake" → "Lk", "River" → "Rv", "Creek" → "Cr", "Mountain" → "Mt"
- Road types: "Road" → "Rd", "Highway" → "Hwy", "Trail" → "Tr", "Interstate" → "I"
- Road designations: "County Road" → "CR", "State Highway" → "SH", "State Route" → "SR", "Interstate 70" → "I70"
- Directions: "near" → "nr", "north of" → "N of", "east" → "E", "west" → "W"
- Locations: "Campground" → "Campgd", "Site" → "S", "mile marker" → "mi"
- Distance: Remove spaces: "5 KM ESE" → "5KM ESE"

Examples (MUST be 50 characters or less):
- "Silver Creek Road near Maple Ridge Lodge at the intersection of County Road 12 and State Highway 29, 3 KM West of Riverside"
  → "Silver Cr Rd CR12/SH29, 3KM W of Riverside" (43 chars - keeps permanent intersection AND city since space allows)
- "Thunder Mountain Campground Site 8 near Eagle Falls"
  → "nr Eagle Falls, S8" (18 chars - permanent geographic feature prioritized)
- "near Willow Creek, County Park" → "nr Willow Cr" (12 chars - creek is permanent)
- "South of Birch River area" → "S of Birch Rv" (13 chars)
- "Interstate 90 at mile marker 42" → "I90 mi 42" (9 chars)

Key Principle: Prioritize findability 50+ years from now. Geographic features and road numbers outlast businesses.
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
