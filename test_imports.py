#!/usr/bin/env python3
"""
Test script to verify imports work correctly.
"""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_import(module_name, description):
    """Test importing a module and report results."""
    try:
        __import__(module_name)
        print(f"✓ {description}: OK")
        return True
    except Exception as e:
        print(f"✗ {description}: FAILED - {str(e)}")
        return False

def main():
    print("Testing imports for LinkedIn adapter and scheduler implementation...")
    print("=" * 60)

    all_passed = True

    # Test timezone utilities
    all_passed &= test_import('app.core.timezone_utils', 'timezone_utils')

    # Test scraper utilities
    all_passed &= test_import('app.core.scraper_utils', 'scraper_utils')

    # Test LinkedIn adapter
    all_passed &= test_import('app.ingestion.job_scraper', 'job_scraper (LinkedInAdapter)')

    # Test API routes
    all_passed &= test_import('app.api.routes', 'API routes')

    # Test specific functions from timezone utils
    if all_passed:
        print("\nTesting specific functions:")
        try:
            from app.core.timezone_utils import get_nz_time, is_business_hours_nz, is_time_for_full_scrape
            nz_time = get_nz_time()
            print(f"✓ get_nz_time(): {nz_time}")
            print(f"✓ is_business_hours_nz(): {is_business_hours_nz()}")
            print(f"✓ is_time_for_full_scrape(): {is_time_for_full_scrape()}")
        except Exception as e:
            print(f"✗ Specific function test failed: {e}")
            all_passed = False

    # Test specific functions from scraper utils
    if all_passed:
        print("\nTesting scraper utilities:")
        try:
            from app.core.scraper_utils import extract_text_safely, extract_attribute_safely, build_url_with_params
            # Mock BeautifulSoup element for testing
            class MockElement:
                def get_text(self, strip=False):
                    return "Test Text" if strip else "Test Text\n"
                def get(self, attr, default=None):
                    return "test_value" if attr == "href" else default

            element = MockElement()
            text = extract_text_safely(element, "default")
            attr = extract_attribute_safely(element, "href", "default")
            url = build_url_with_params("https://example.com", {"param": "value"})
            print(f"✓ extract_text_safely(): {text}")
            print(f"✓ extract_attribute_safely(): {attr}")
            print(f"✓ build_url_with_params(): {url}")
        except Exception as e:
            print(f"✗ Scraper utility test failed: {e}")
            all_passed = False

    print("=" * 60)
    if all_passed:
        print("✓ All tests passed!")
        return 0
    else:
        print("✗ Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())