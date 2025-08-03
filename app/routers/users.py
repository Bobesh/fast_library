import logging
from typing import List, Optional
from datetime import date
from dataclasses import asdict
from pydantic import BaseModel, EmailStr, Field, computed_field
from fastapi import APIRouter, HTTPException, status, Depends
from app.services.users_manager import UserManager
from app.core.dependencies import user_manager_dependency
from app.core.logging import log_debug

logger = logging.getLogger(__name__)
router = APIRouter()


# INPUT Pydantic models (VIEW layer)
class UserCreateRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="Username (3-50 characters)")
    email: EmailStr = Field(..., description="Valid email address")
    first_name: str = Field(..., min_length=1, max_length=100, description="First name")
    last_name: str = Field(..., min_length=1, max_length=100, description="Last name")
    phone: Optional[str] = Field(None, max_length=20, description="Phone number")


class UserUpdateRequest(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    active: Optional[bool] = None


# OUTPUT Pydantic models (responses)
class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    first_name: str
    last_name: str
    phone: Optional[str] = None
    active: bool
    created_at: date

    @computed_field
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


class BorrowingHistoryResponse(BaseModel):
    book_title: str
    borrowed_at: date
    due_date: date
    returned_at: Optional[date] = None
    is_active: bool
    is_overdue: bool


class UserWithHistoryResponse(UserResponse):
    borrowing_history: List[BorrowingHistoryResponse]


class UserCreatedResponse(BaseModel):
    message: str
    user: UserResponse


class UserUpdatedResponse(BaseModel):
    message: str
    user: UserResponse


class UserActionResponse(BaseModel):
    message: str
    user: UserResponse


# Helper functions
def dataclass_to_pydantic(dataclass_obj, pydantic_model):
    """Convert dataclass to pydantic model"""
    return pydantic_model.model_validate(asdict(dataclass_obj))


def convert_dataclass_list(dataclass_list, pydantic_model):
    """Convert list of dataclasses to list of pydantic models"""
    return [dataclass_to_pydantic(item, pydantic_model) for item in dataclass_list]


def pydantic_to_dict(pydantic_obj: BaseModel) -> dict:
    """Convert Pydantic model to dict, excluding None values"""
    return pydantic_obj.model_dump(exclude_none=True)


# API Endpoints
@router.get("/", response_model=List[UserResponse])
async def get_users(
        active_only: bool = Field(True, description="Filter only active users"),
        user_manager: UserManager = Depends(user_manager_dependency)
):
    """Get all users, optionally filter by active status"""
    log_debug(logger, f"GET /users endpoint called (active_only={active_only})")
    users = await user_manager.get_all_users(active_only=active_only)
    return convert_dataclass_list(users, UserResponse)


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
    return dataclass_to_pydantic(user, UserResponse)


@router.get("/{user_id}/history", response_model=List[BorrowingHistoryResponse])
async def get_user_borrowing_history(
        user_id: int,
        include_active: bool = Field(True, description="Include active borrowings"),
        user_manager: UserManager = Depends(user_manager_dependency)
):
    """Get borrowing history for user"""
    log_debug(logger, f"GET /users/{user_id}/history endpoint called")

    # Check if user exists first
    user = await user_manager.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )

    history = await user_manager.get_user_borrowing_history(user_id, include_active)
    return [BorrowingHistoryResponse.model_validate(record) for record in history]


@router.post("/", response_model=UserCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
        user_data: UserCreateRequest,
        user_manager: UserManager = Depends(user_manager_dependency)
):
    """Create a new user"""
    log_debug(logger, f"POST /users endpoint called for username: {user_data.username}")
    try:
        # Convert Pydantic model to dict for manager
        user_dict = pydantic_to_dict(user_data)
        created_user = await user_manager.create_user(user_dict)

        return UserCreatedResponse(
            message="User created successfully",
            user=dataclass_to_pydantic(created_user, UserResponse)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/{user_id}", response_model=UserUpdatedResponse)
async def update_user(
        user_id: int,
        user_data: UserUpdateRequest,
        user_manager: UserManager = Depends(user_manager_dependency)
):
    """Update user information"""
    log_debug(logger, f"PUT /users/{user_id} endpoint called")
    try:
        # Convert Pydantic model to dict, excluding None values
        user_dict = pydantic_to_dict(user_data)

        if not user_dict:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields provided for update"
            )

        updated_user = await user_manager.update_user(user_id, user_dict)
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found"
            )

        return UserUpdatedResponse(
            message="User updated successfully",
            user=dataclass_to_pydantic(updated_user, UserResponse)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.patch("/{user_id}/deactivate", response_model=UserActionResponse)
async def deactivate_user(
        user_id: int,
        user_manager: UserManager = Depends(user_manager_dependency)
):
    """Deactivate a user (only if no active borrowings)"""
    log_debug(logger, f"PATCH /users/{user_id}/deactivate endpoint called")
    try:
        deactivated_user = await user_manager.deactivate_user(user_id)
        if not deactivated_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found"
            )

        return UserActionResponse(
            message="User deactivated successfully",
            user=dataclass_to_pydantic(deactivated_user, UserResponse)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.patch("/{user_id}/activate", response_model=UserActionResponse)
async def activate_user(
        user_id: int,
        user_manager: UserManager = Depends(user_manager_dependency)
):
    """Activate a user"""
    log_debug(logger, f"PATCH /users/{user_id}/activate endpoint called")
    try:
        activated_user = await user_manager.activate_user(user_id)
        if not activated_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found"
            )

        return UserActionResponse(
            message="User activated successfully",
            user=dataclass_to_pydantic(activated_user, UserResponse)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
        user_id: int,
        user_manager: UserManager = Depends(user_manager_dependency)
):
    """
    Soft delete user (deactivate)
    Note: We don't actually delete users to preserve borrowing history
    """
    log_debug(logger, f"DELETE /users/{user_id} endpoint called (soft delete)")
    try:
        deactivated_user = await user_manager.deactivate_user(user_id)
        if not deactivated_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found"
            )
        # 204 No Content - no response body
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )