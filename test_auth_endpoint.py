#!/usr/bin/env python3
"""
Test script to verify that the authentication logic for resume endpoints works correctly.
"""

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from typing import Optional, Dict
import uuid

# Mock settings
class Settings:
    JWT_SECRET_KEY = "test-secret-key"
    JWT_ALGORITHM = "HS256"
    JWT_EXPIRE_MINUTES = 60

settings = Settings()

# Mock database and User model
class User:
    def __init__(self, id: int, email: str, is_active: bool = True):
        self.id = id
        self.email = email
        self.is_active = is_active

# Mock database session
class MockDB:
    def __init__(self):
        self.users = {
            1: User(1, "test@example.com"),
            2: User(2, "test2@example.com")
        }

    async def execute(self, query):
        # Simulate SELECT * FROM users WHERE id = ?
        # This is a simplified mock - in reality we'd parse the query
        class MockResult:
            def __init__(self, user):
                self.user = user
            def scalar_one_or_none(self):
                return self.user
        # For simplicity, assume query is for user with id=1
        return MockResult(self.users.get(1))

# Mock security schemes
bearer_scheme = HTTPBearer(auto_error=False)

def _auth_enabled() -> bool:
    return bool(settings.JWT_SECRET_KEY)

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: MockDB = Depends(lambda: MockDB()),
) -> Optional[User]:
    if not _auth_enabled():
        return None
    if not credentials:
        # This is where the "Not authenticated" error comes from
        print(f"DEBUG: No credentials provided")
        return None
    try:
        print(f"DEBUG: Attempting to decode token: {credentials.credentials}")
        payload = jwt.decode(credentials.credentials, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id = int(payload.get("sub"))
        print(f"DEBUG: Decoded token, user_id: {user_id}")
    except (JWTError, ValueError, TypeError) as e:
        print(f"DEBUG: Token validation failed: {e}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        print(f"DEBUG: User not found or inactive: {user}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    print(f"DEBUG: User authenticated successfully: {user.email}")
    return user

async def require_user(user: Optional[User] = Depends(get_current_user)) -> User:
    if user is None:
        print("DEBUG: require_user - user is None, raising authentication required")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    print(f"DEBUG: require_user - user validated: {user.email}")
    return user

# Mock the profile data retrieval
async def fake_get_profile(profile_id: int, db_session: MockDB, user_id: int) -> dict:
    # Simulate the profile service query
    class MockResult:
        def __init__(self, data):
            self.data = data
        def scalar_one_or_none(self):
            return self.data

    # Simulate: select * from career_profiles where id = ? and user_id = ?
    if user_id == 1 and profile_id == 1:
        return {"id": 1, "user_id": 1, "full_name": "Test User"}
    return None

async def fake_get_profile_structured(profile_id: int, db_session: MockDB, user_id: int) -> dict:
    # Simulate the _get_profile_structured function
    if user_id == 1 and profile_id == 1:
        return {
            "id": 1,
            "user_id": 1,
            "full_name": "Test User",
            "email": "test@example.com",
            "raw_resume_text": "Sample resume text"
        }
    return None

# Create test app
app = FastAPI()

@app.get("/api/profile/{profile_id}/resume/html")
async def download_base_resume_html(
    profile_id: int,
    user: User = Depends(require_user),
    download: bool = Query(default=False, description="Force download instead of inline display"),
    db_session: MockDB = Depends(lambda: MockDB()),
):
    print(f"DEBUG: Endpoint entered, user_id: {user.id if user else None}")

    # Simulate the database query for profile ownership check
    # select * from career_profiles where id = ? and user_id = ?
    if user.id == 1 and profile_id == 1:
        profile = {"id": 1, "user_id": 1, "full_name": "Test User", "formatted_resume_html": "<h1>Test Resume</h1>"}
    else:
        profile = None

    if not profile:
        print(f"DEBUG: Profile not found or access denied for profile_id={profile_id}, user_id={user.id}")
        raise HTTPException(status_code=404, detail="Profile not found")

    html = profile["formatted_resume_html"] or ""
    if not html:
        print(f"DEBUG: No existing HTML, generating from structured data")
        profile_data = await fake_get_profile_structure(profile_id, db_session, user.id)
        if not profile_data:
            print(f"DEBUG: Could not get structured profile data")
            raise HTTPException(status_code=404, detail="Profile data not found")
        html = f"<h1>{profile_data['full_name']}</h1><p>{profile_data['raw_resume_text']}</h1>"

    # Return HTML response
    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=html)

# Test the endpoint
if __name__ == "__main__":
    import asyncio
    from fastapi.testclient import TestClient

    client = TestClient(app)

    print("=" * 50)
    print("Testing authentication for resume endpoint")
    print("=" * 50)

    # Test 1: No auth header (should fail)
    print("\nTest 1: Request without authorization header")
    response = client.get("/api/profile/1/resume/html")
    print(f"Status: {response.status_code}")
    if response.status_code == 401:
        print("Expected: Got 401 Unauthorized")
        try:
            error_data = response.json()
            print(f"Error detail: {error_data.get('detail')}")
        except:
            print(f"Error response: {response.text}")
    else:
        print(f"Unexpected status code: {response.status_code}")
        print(f"Response: {response.text}")

    # Test 2: With valid auth header (should succeed)
    print("\nTest 2: Request with valid authorization header")
    # Create a test token for user_id=1
    test_token = jwt.encode({"sub": "1", "exp": 9999999999}, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    headers = {"Authorization": f"Bearer {test_token}"}
    response = client.get("/api/profile/1/resume/html", headers=headers)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print("Success: Got 200 OK")
        print(f"Response length: {len(response.text)} characters")
        print(f"First 100 chars: {response.text[:100]}...")
    elif response.status_code == 401:
        print("Failed: Got 401 Unauthorized - this indicates the auth issue")
        try:
            error_data = response.json()
            print(f"Error detail: {error_data.get('detail')}")
        except:
            print(f"Error response: {response.text}")
    else:
        print(f"Unexpected status code: {response.status_code}")
        print(f"Response: {response.text}")

    print("\n" + "=" * 50)
    print("Test complete")
    print("=" * 50)