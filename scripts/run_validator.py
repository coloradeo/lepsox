#!/usr/bin/env python3
"""
Command-line script to run LepSoc validator
"""
import sys
import os
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from lepsox import LepSocValidationCrew


def main():
    """Main execution function"""
    print("LepSoc Season Summary Validation System")
    print("=" * 50)

    # Check for --no-inat flag first
    use_inat = '--no-inat' not in sys.argv
    if not use_inat:
        print("(Running without iNaturalist MCP integration)")
        sys.argv.remove('--no-inat')

    # Check command line arguments
    if len(sys.argv) < 2:
        print("Usage: python run_validator.py [--no-inat] <input_file> [output_file]")
        print("\nExample:")
        print("  python scripts/run_validator.py tests/fixtures/test_with_errors.xlsx output.xlsx")
        print("  python scripts/run_validator.py --no-inat tests/fixtures/test_with_errors.xlsx output.xlsx")
        sys.exit(1)

    input_file = sys.argv[1]

    # Generate output filename with timestamp
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
        # Add timestamp before extension
        base, ext = os.path.splitext(output_file)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"{base}_{timestamp}{ext}"
    else:
        # Default output: input_validated_YYYYMMDD_HHMMSS.xlsx
        base, ext = os.path.splitext(input_file)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"{base}_validated_{timestamp}{ext}"

    # Verify input file exists
    if not os.path.exists(input_file):
        print(f"Error: Input file not found: {input_file}")
        sys.exit(1)

    # Create validation crew
    print(f"\nInitializing validation crew...")
    crew = LepSocValidationCrew(use_inat=use_inat)

    # Run validation
    print(f"Processing file: {input_file}")
    validated_df = crew.validate_file(input_file, output_file)

    print(f"\n✓ Validation complete!")
    print(f"Output saved to: {output_file}")


if __name__ == "__main__":
    main()
