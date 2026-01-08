#!/usr/bin/env python3
"""
Test script for YouTube URL extraction.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers import YouTubeScraper


def test_url_extraction():
    """Test URL extraction with various formats."""
    scraper = YouTubeScraper()

    test_cases = [
        # (url, expected_identifier)
        ("https://www.youtube.com/@mkbhd", "@mkbhd"),
        ("https://youtube.com/@veritasium", "@veritasium"),
        ("http://www.youtube.com/@LinusTechTips", "@LinusTechTips"),
        ("youtube.com/@TomScott", "@TomScott"),

        ("https://www.youtube.com/c/Veritasium", "Veritasium"),
        ("https://youtube.com/c/CGPGrey", "CGPGrey"),

        ("https://www.youtube.com/channel/UCBJycsmduvYEL83R_U4JriQ", "UCBJycsmduvYEL83R_U4JriQ"),
        ("https://youtube.com/channel/UC6nSFpj9HTCZ5t-N3Rm3-HA", "UC6nSFpj9HTCZ5t-N3Rm3-HA"),

        ("https://www.youtube.com/user/CGPGrey", "CGPGrey"),
        ("https://youtube.com/user/LinusTechTips", "LinusTechTips"),
    ]

    print("Testing YouTube URL extraction:\n")
    passed = 0
    failed = 0

    for url, expected in test_cases:
        try:
            result = scraper.extract_username(url)
            if result == expected:
                print(f"✓ PASS: {url}")
                print(f"  → {result}")
                passed += 1
            else:
                print(f"✗ FAIL: {url}")
                print(f"  Expected: {expected}")
                print(f"  Got: {result}")
                failed += 1
        except Exception as e:
            print(f"✗ ERROR: {url}")
            print(f"  {e}")
            failed += 1

        print()

    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0


if __name__ == "__main__":
    success = test_url_extraction()
    sys.exit(0 if success else 1)
