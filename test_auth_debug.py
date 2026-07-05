#!/usr/bin/env python3
"""
Debug script to test authentication setup
"""

import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.core.config import settings
from app.api.auth import _auth_enabled

def test_auth_config():
    print("=== Authentication Configuration Test ===")
    print(f"JWT_SECRET_KEY: '{settings.JWT_SECRET_KEY}'")
    print(f"JWT_SECRET_KEY length: {len(settings.JWT_SECRET_KEY)}")
    print(f"_auth_enabled(): {_auth_enabled()}")
    print(f"bool(settings.JWT_SECRET_KEY): {bool(settings.JWT_SECRET_KEY)}")

    if _auth_enabled():
        print("✅ Authentication IS enabled")
    else:
        print("❌ Authentication is DISABLED (empty JWT_SECRET_KEY)")

    print()

if __name__ == "__main__":
    test_auth_config()