"""
Temporal field validators (First Date, Last Date, Year)
"""
from typing import Any, Dict
import pandas as pd
import re
from datetime import datetime

from .base import BaseValidator
from ..models.validation_result import ValidationResult
from ..config import DATE_FORMAT


class FirstDateValidator(BaseValidator):
    """Agent 12: Validate First Date field (Column L)"""

    def __init__(self):
        super().__init__('First Date')

    def validate(self, value: Any, row_data: Dict = None) -> ValidationResult:
        result = ValidationResult(self.field_name, value)

        if pd.isna(value) or value == '':
            result.is_valid = False
            result.errors.append("First Date is required")
            return result

        date_obj = None

        # Handle datetime objects from Excel (default format)
        if isinstance(value, (datetime, pd.Timestamp)):
            date_obj = value if isinstance(value, datetime) else value.to_pydatetime()

        # Handle string format - try to parse it
        elif isinstance(value, str):
            date_str = str(value).strip()

            # Check if already in correct format (dd-mmm-yy)
            if re.match(DATE_FORMAT, date_str.upper()):
                # Already correct format, validate it's sensible
                try:
                    date_parts = date_str.upper().split('-')
                    if len(date_parts) == 3:
                        day = int(date_parts[0])
                        month_str = date_parts[1]
                        year = int(date_parts[2])

                        # Convert 2-digit year to 4-digit for parsing
                        year_full = 2000 + year if year < 50 else 1900 + year

                        # Parse to validate
                        date_obj = datetime.strptime(f"{day}-{month_str}-{year_full}", "%d-%b-%Y")

                        # Already in correct format, no correction needed
                        result.metadata['datetime'] = date_obj
                except Exception as e:
                    result.is_valid = False
                    result.errors.append(f"Invalid date: {date_str}")
                    return result
            else:
                # Try to parse various formats
                try:
                    # Try common formats
                    for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%m/%d/%y', '%d/%m/%Y', '%d/%m/%y']:
                        try:
                            date_obj = datetime.strptime(date_str, fmt)
                            break
                        except:
                            continue

                    if date_obj is None:
                        result.is_valid = False
                        result.errors.append(f"Could not parse date: {date_str}")
                        return result
                except:
                    result.is_valid = False
                    result.errors.append(f"Invalid date format: {date_str}")
                    return result

        # Convert to standard format: dd-mmm-yy
        if date_obj:
            formatted_date = date_obj.strftime("%d-%b-%y").upper()

            # Set correction if different from input
            if str(value) != formatted_date:
                result.correction = formatted_date
                result.correction_type = "normalization"  # Format standardization, not a real correction

            # Check if date is reasonable (within last 3 years)
            current_year = datetime.now().year
            if current_year - date_obj.year > 3:
                result.warnings.append(f"Date is more than 3 years old: {date_obj.year}")

            # Check if date is in the future
            if date_obj > datetime.now():
                result.is_valid = False
                result.errors.append(f"Date cannot be in the future: {formatted_date}")

            result.metadata['datetime'] = date_obj

        return result


class LastDateValidator(BaseValidator):
    """Agent 13: Validate Last Date field (Column M)"""

    def __init__(self):
        super().__init__('Last Date')

    def validate(self, value: Any, row_data: Dict = None) -> ValidationResult:
        result = ValidationResult(self.field_name, value)

        # Optional field
        if pd.isna(value) or value == '':
            return result

        date_obj = None

        # Handle datetime objects from Excel (default format)
        if isinstance(value, (datetime, pd.Timestamp)):
            date_obj = value if isinstance(value, datetime) else value.to_pydatetime()

        # Handle string format - try to parse it
        elif isinstance(value, str):
            date_str = str(value).strip()

            # Check if already in correct format (dd-mmm-yy)
            if re.match(DATE_FORMAT, date_str.upper()):
                # Already correct format, validate it's sensible
                try:
                    date_parts = date_str.upper().split('-')
                    if len(date_parts) == 3:
                        day = int(date_parts[0])
                        month_str = date_parts[1]
                        year = int(date_parts[2])

                        # Convert 2-digit year to 4-digit for parsing
                        year_full = 2000 + year if year < 50 else 1900 + year

                        # Parse to validate
                        date_obj = datetime.strptime(f"{day}-{month_str}-{year_full}", "%d-%b-%Y")

                        # Already in correct format, no correction needed
                        result.metadata['datetime'] = date_obj
                except Exception as e:
                    result.is_valid = False
                    result.errors.append(f"Invalid date: {date_str}")
                    return result
            else:
                # Try to parse various formats
                try:
                    # Try common formats
                    for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%m/%d/%y', '%d/%m/%Y', '%d/%m/%y']:
                        try:
                            date_obj = datetime.strptime(date_str, fmt)
                            break
                        except:
                            continue

                    if date_obj is None:
                        result.is_valid = False
                        result.errors.append(f"Could not parse date: {date_str}")
                        return result
                except:
                    result.is_valid = False
                    result.errors.append(f"Invalid date format: {date_str}")
                    return result

        # Convert to standard format: dd-mmm-yy
        if date_obj:
            formatted_date = date_obj.strftime("%d-%b-%y").upper()

            # Set correction if different from input
            if str(value) != formatted_date:
                result.correction = formatted_date
                result.correction_type = "normalization"  # Format standardization, not a real correction

            # Compare with First Date if available
            first_date = row_data.get('First Date') if row_data else None
            if first_date:
                # Get First Date datetime object
                first_dt = None
                if isinstance(first_date, (datetime, pd.Timestamp)):
                    first_dt = first_date if isinstance(first_date, datetime) else first_date.to_pydatetime()
                elif isinstance(first_date, str) and re.match(DATE_FORMAT, first_date.upper()):
                    try:
                        date_parts = first_date.upper().split('-')
                        day = int(date_parts[0])
                        month_str = date_parts[1]
                        year = int(date_parts[2])
                        year_full = 2000 + year if year < 50 else 1900 + year
                        first_dt = datetime.strptime(f"{day}-{month_str}-{year_full}", "%d-%b-%Y")
                    except:
                        pass

                if first_dt and date_obj < first_dt:
                    result.warnings.append("Last Date is before First Date")

            # Check if date is in the future
            if date_obj > datetime.now():
                result.is_valid = False
                result.errors.append(f"Date cannot be in the future: {formatted_date}")

            result.metadata['datetime'] = date_obj

        return result


class YearValidator(BaseValidator):
    """Agent 16: Validate Year field (Column P)"""

    def __init__(self):
        super().__init__('Year')

    def validate(self, value: Any, row_data: Dict = None) -> ValidationResult:
        result = ValidationResult(self.field_name, value)

        # If Year is empty but First Date exists, extract year from it
        if (pd.isna(value) or value == '') and row_data:
            first_date = row_data.get('First Date')
            if first_date and isinstance(first_date, (datetime, pd.Timestamp)):
                date_obj = first_date if isinstance(first_date, datetime) else first_date.to_pydatetime()
                result.correction = date_obj.year
                result.correction_type = "correction"  # Auto-fill is a real correction
                result.warnings.append(f"Year auto-filled from First Date: {date_obj.year}")
                return result
            else:
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
