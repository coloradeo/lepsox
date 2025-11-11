#!/usr/bin/env python3
"""
Test connections to Ollama and iNaturalist MCP servers
"""
import sys
import os
import asyncio
import httpx

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from lepsox.config import OLLAMA_BASE_URL, INAT_MCP_URL
from lepsox.integrations import INatValidator


def test_ollama():
    """Test Ollama server connection"""
    print("Testing Ollama server...")
    print(f"  URL: {OLLAMA_BASE_URL}")

    try:
        response = httpx.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=10.0)
        if response.status_code == 200:
            models = response.json().get('models', [])
            print(f"  ✓ Connected!")
            print(f"  ✓ Available models: {len(models)}")
            if models:
                print(f"    - {models[0]['name']}")
                if len(models) > 1:
                    print(f"    ... and {len(models) - 1} more")
            return True
        else:
            print(f"  ✗ Failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"  ✗ Connection failed: {e}")
        return False


async def test_inat():
    """Test iNaturalist MCP server connection"""
    print("\nTesting iNaturalist MCP server...")
    print(f"  URL: {INAT_MCP_URL}")

    try:
        validator = INatValidator()

        # Test species search
        result = await validator.check_species("Danaus", "plexippus")

        if result.get('valid'):
            print(f"  ✓ Connected!")
            print(f"  ✓ Test search successful:")
            print(f"    Species: {result.get('correct_name')}")
            print(f"    Common: {result.get('common_name')}")
            print(f"    Taxon ID: {result.get('taxon_id')}")
            return True
        else:
            print(f"  ✗ Search failed: {result.get('error')}")
            return False

    except Exception as e:
        print(f"  ✗ Connection failed: {e}")
        return False


def main():
    """Main test function"""
    print("="*60)
    print("LepSoc Validation System - Connection Test")
    print("="*60)

    # Test Ollama
    ollama_ok = test_ollama()

    # Test iNat (async)
    inat_ok = asyncio.run(test_inat())

    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Ollama:       {'✓ PASS' if ollama_ok else '✗ FAIL'}")
    print(f"iNaturalist:  {'✓ PASS' if inat_ok else '✗ FAIL'}")
    print("="*60)

    if ollama_ok and inat_ok:
        print("\n✓ All systems ready!")
        sys.exit(0)
    else:
        print("\n✗ Some services are unavailable")
        sys.exit(1)


if __name__ == "__main__":
    main()
