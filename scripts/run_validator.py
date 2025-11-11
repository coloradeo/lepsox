#!/usr/bin/env python3
"""
Command-line script to run LepSoc validator
"""
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from lepsox import LepSocValidationCrew


def main():
    """Main execution function"""
    print("LepSoc Season Summary Validation System")
    print("=" * 50)

    # Check command line arguments
    if len(sys.argv) < 2:
        print("Usage: python run_validator.py <input_file> [output_file]")
        print("\nExample:")
        print("  python scripts/run_validator.py tests/fixtures/test_with_errors.xlsx output.xlsx")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else input_file.replace('.', '_validated.')

    # Verify input file exists
    if not os.path.exists(input_file):
        print(f"Error: Input file not found: {input_file}")
        sys.exit(1)

    # Create validation crew
    print(f"\nInitializing validation crew...")
    crew = LepSocValidationCrew()

    # Run validation
    print(f"Processing file: {input_file}")
    validated_df = crew.validate_file(input_file, output_file)

    print(f"\n✓ Validation complete!")
    print(f"Output saved to: {output_file}")


if __name__ == "__main__":
    main()
