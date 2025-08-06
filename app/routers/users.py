import logging
from typing import List
from datetime import date
from dataclasses import asdict
from pydantic import BaseModel, EmailStr, Field, computed_field
from fastapi import APIRouter, HTTPException, status, Depends
from app.core.dependencies import user_manager_dependency
from app.core.logging import log_debug
from app.services.users_manager import UserManager

logger = logging.getLogger(__name__)
router = APIRouter()


# INPUT Pydantic models (VIEW layer)
class UserCreateRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="Username (3-50 characters)")
    email: EmailStr = Field(..., description="Valid email address")
    first_name: str = Field(..., min_length=1, max_length=100, description="First name")
    last_name: str = Field(..., min_length=1, max_length=100, description="Last name")


# OUTPUT Pydantic models (responses)
class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    first_name: str
    last_name: str
    created_at: date

    @computed_field
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


class UserCreatedResponse(BaseModel):
    message: str
    user: UserResponse


# API Endpoints
@router.get("/", response_model=List[UserResponse])
async def get_users(user_manager: UserManager = Depends(user_manager_dependency)):
    """Get all users"""
    log_debug(logger, "GET /users endpoint called")
    users = await user_manager.get_all_users()

    return [
        UserResponse.model_validate(asdict(user))
        for user in users
    ]


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
        user_id: int,
        user_manager: UserManager = Depends(user_manager_dependency)
):
    """Get user by ID"""
    log_debug(logger, f"GET /users/{user_id} endpoint called")
    user = await user_manager.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )

    return UserResponse.model_validate(asdict(user))


@router.post("/", response_model=UserCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
        user_data: UserCreateRequest,
        user_manager: UserManager = Depends(user_manager_dependency)
):
    """Create a new user"""
    log_debug(logger, f"POST /users endpoint called for username: {user_data.username}")
    try:
        user_dict = user_data.model_dump(exclude_none=True)
        created_user = await user_manager.create_user(user_dict)

        return UserCreatedResponse(
            message="User created successfully",
            user=UserResponse.model_validate(asdict(created_user))
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )