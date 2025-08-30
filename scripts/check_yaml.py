#!/usr/bin/env python3
"""
Quick sanity check script to verify PyYAML is working correctly.
Run this after installing dependencies to ensure yaml import works.
"""

import io

import yaml


def main():
    """Test basic yaml functionality."""
    try:
        # Test safe_load
        test_data = yaml.safe_load(io.StringIO("a: 1"))
        print(f"yaml.safe_load test passed: {test_data}")

        # Test safe_dump
        test_dict = {"test": "value", "number": 42}
        dumped = yaml.safe_dump(test_dict)
        print(f"yaml.safe_dump test passed: {dumped.strip()}")

        print("✅ yaml ok - all tests passed!")
        return True

    except Exception as e:
        print(f"❌ yaml test failed: {e}")
        return False

if __name__ == "__main__":
    main()
