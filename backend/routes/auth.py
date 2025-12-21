"""authentication endpoints for user management"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from backend.models.user import UserDatabase

router = APIRouter(prefix="/auth", tags=["auth"])
user_db = UserDatabase()


class LoginRequest(BaseModel):
    """login request model"""
    email: str
    password: str


class LoginResponse(BaseModel):
    """login response model"""
    user_id: str
    name: str
    email: str
    preferred_language: str
    token: str  # simplified: just user_id for demo


class UserStatsResponse(BaseModel):
    """user statistics response"""
    user_id: str
    name: str
    email: str
    preferred_language: str
    usage: dict


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    authenticate user and return session token

    args:
        request: login credentials

    returns:
        user info with session token
    """
    user = user_db.authenticate(request.email, request.password)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="invalid email or password"
        )

    return LoginResponse(
        user_id=user.id,
        name=user.name,
        email=user.email,
        preferred_language=user.preferred_language,
        token=user.id  # simplified token for demo
    )


@router.get("/users/{user_id}/stats", response_model=UserStatsResponse)
async def get_user_stats(user_id: str):
    """
    get user statistics and usage

    args:
        user_id: user identifier

    returns:
        user info with usage statistics
    """
    user = user_db.get_user(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="user not found")

    usage = user_db.get_user_usage(user_id) or {}

    return UserStatsResponse(
        user_id=user.id,
        name=user.name,
        email=user.email,
        preferred_language=user.preferred_language,
        usage=usage
    )


@router.get("/demo-users")
async def get_demo_users():
    """
    get list of demo user emails for testing

    returns:
        list of demo user credentials
    """
    return {
        "demo_users": [
            {"email": "sarah.cohen@example.com", "password": "demo123", "language": "en", "name": "Sarah Cohen"},
            {"email": "david.miller@example.com", "password": "demo123", "language": "en", "name": "David Miller"},
            {"email": "emma.taylor@example.com", "password": "demo123", "language": "en", "name": "Emma Taylor"},
            {"email": "rachel.levi@example.com", "password": "demo123", "language": "he", "name": "Rachel Levi"},
            {"email": "yael.rosenberg@example.com", "password": "demo123", "language": "he", "name": "Yael Rosenberg"},
            {"email": "dmitry.ivanov@example.com", "password": "demo123", "language": "ru", "name": "Dmitry Ivanov"},
            {"email": "anastasia.petrova@example.com", "password": "demo123", "language": "ru", "name": "Anastasia Petrova"},
            {"email": "alexander.volkov@example.com", "password": "demo123", "language": "ru", "name": "Alexander Volkov"},
            {"email": "omar.hassan@example.com", "password": "demo123", "language": "ar", "name": "Omar Hassan"},
            {"email": "fatima.ali@example.com", "password": "demo123", "language": "ar", "name": "Fatima Ali"},
        ],
        "note": "all demo users have password: demo123"
    }
