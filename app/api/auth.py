from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import User, SecretQuestion, get_db

router = APIRouter(prefix="/api/auth", tags=["auth"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)


def _auth_enabled() -> bool:
    return bool(settings.JWT_SECRET_KEY)


def create_access_token(user_id: int) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": str(user_id), "exp": expire},
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    if not _auth_enabled():
        return None
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = jwt.decode(credentials.credentials, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError, TypeError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


async def require_user(user: Optional[User] = Depends(get_current_user)) -> User:
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return user


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str = ""


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


@router.post("/register", response_model=AuthResponse)
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    if not _auth_enabled():
        raise HTTPException(status_code=503, detail="Authentication not configured")

    existing = await db.execute(select(User).where(User.email == request.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=request.email,
        hashed_password=pwd_context.hash(request.password),
        full_name=request.full_name,
    )
    db.add(user)
    await db.flush()

    token = create_access_token(user.id)
    return AuthResponse(
        access_token=token,
        user={"id": user.id, "email": user.email, "full_name": user.full_name},
    )


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    if not _auth_enabled():
        raise HTTPException(status_code=503, detail="Authentication not configured")

    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()
    if not user or not pwd_context.verify(request.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(user.id)
    return AuthResponse(
        access_token=token,
        user={"id": user.id, "email": user.email, "full_name": user.full_name},
    )


@router.get("/me")
async def get_me(user: User = Depends(require_user)):
    return {"id": user.id, "email": user.email, "full_name": user.full_name, "is_active": user.is_active}


class SetSecretQuestionsRequest(BaseModel):
    questions: list[dict]


class ForgotPasswordRequest(BaseModel):
    email: EmailStr
    answers: list[dict]
    new_password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@router.post("/set-secret-questions")
async def set_secret_questions(
    request: SetSecretQuestionsRequest,
    user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(
        select(SecretQuestion).where(SecretQuestion.user_id == user.id)
    )
    for sq in existing.scalars().all():
        await db.delete(sq)

    for qa in request.questions:
        sq = SecretQuestion(
            user_id=user.id,
            question=qa["question"],
            answer_hash=pwd_context.hash(qa["answer"].lower().strip()),
        )
        db.add(sq)

    await db.flush()
    return {"message": "Secret questions set successfully"}


@router.get("/secret-questions/{email}")
async def get_secret_questions(email: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        return {"questions": []}

    result = await db.execute(
        select(SecretQuestion).where(SecretQuestion.user_id == user.id)
    )
    questions = [{"id": sq.id, "question": sq.question} for sq in result.scalars().all()]
    return {"questions": questions}


@router.post("/forgot-password")
async def forgot_password(request: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = await db.execute(
        select(SecretQuestion).where(SecretQuestion.user_id == user.id)
    )
    stored_questions = {sq.question: sq.answer_hash for sq in result.scalars().all()}

    for answer_data in request.answers:
        question = answer_data["question"]
        answer = answer_data["answer"].lower().strip()
        if question not in stored_questions:
            raise HTTPException(status_code=400, detail=f"Invalid question: {question}")
        if not pwd_context.verify(answer, stored_questions[question]):
            raise HTTPException(status_code=400, detail="Incorrect answer")

    user.hashed_password = pwd_context.hash(request.new_password)
    await db.flush()
    return {"message": "Password reset successfully"}


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    if not pwd_context.verify(request.current_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    user.hashed_password = pwd_context.hash(request.new_password)
    await db.flush()
    return {"message": "Password changed successfully"}
