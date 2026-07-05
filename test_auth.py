#!/usr/bin/env python3
"""
Simple test script to verify that the authentication fix works correctly.
This tests that the get_my_profile endpoint properly passes the user_id parameter.
"""

import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def test_imports():
    """Test that we can import the necessary modules without errors."""
    try:
        from app.api.routes import router
        from app.services.profile_service import ProfileService
        print("✓ Successfully imported modules")
        return True
    except Exception as e:
        print(f"✗ Failed to import modules: {e}")
        return False

def test_get_my_profile_call():
    """Test that the get_my_profile function calls profile_service.get_profile with correct parameters."""
    # We can't easily test the actual async function without a database,
    # but we can verify the source code contains the correct call

    try:
        with open('app/api/routes.py', 'r') as f:
            content = f.read()

        # Check for the correct pattern in the get_my_profile function
        if 'return await profile_service.get_profile(profile.id, db_session, user_id=user.id)' in content:
            print("✓ get_my_profile correctly calls profile_service.get_profile with user_id")
            return True
        else:
            print("✗ get_my_profile does not have the correct call to profile_service.get_profile")
            # Show what it actually has
            import re
            match = re.search(r'return await profile_service\.get_profile\([^)]+\)', content)
            if match:
                print(f"  Found: {match.group()}")
            return False
    except Exception as e:
        print(f"✗ Error checking get_my_profile: {e}")
        return False

def main():
    """Run all tests."""
    print("Testing authentication fix...")
    print("=" * 50)

    tests = [
        test_imports,
        test_get_my_profile_call
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1
        print()

    print("=" * 50)
    print(f"Tests passed: {passed}/{total}")

    if passed == total:
        print("✓ All tests passed! The authentication fix appears to be correct.")
        return 0
    else:
        print("✗ Some tests failed. Please review the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())