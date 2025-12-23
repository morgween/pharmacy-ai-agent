"""authentication endpoints for user management"""
import asyncio
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
    token: str


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
    user = await asyncio.to_thread(
        user_db.authenticate,
        request.email,
        request.password
    )

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
        token=user.id
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
    user = await asyncio.to_thread(user_db.get_user, user_id)

    if not user:
        raise HTTPException(status_code=404, detail="user not found")

    usage = await asyncio.to_thread(user_db.get_user_usage, user_id) or {}

    return UserStatsResponse(
        user_id=user.id,
        name=user.name,
        email=user.email,
        preferred_language=user.preferred_language,
        usage=usage
    )
