from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import timedelta
from app.database import get_db
from app.schemas import UserCreate, UserResponse, UserUpdate, UserListResponse, RoleUpdate, TokenResponse
from app.crud import user_crud
from app.utils.auth import verify_token, create_access_token, create_refresh_token
from app.core.config import get_settings

router = APIRouter()
settings = get_settings()

def get_current_user(token: str = Depends(verify_token)):
    """Получить текущего пользователя из токена"""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    return token

def require_admin(current_user: dict = Depends(get_current_user)):
    """Проверить права администратора"""
    if current_user.get("role") != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user

@router.post("/", response_model=UserResponse)
async def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """Создать пользователя"""
    existing_user = user_crud.get_user_by_email(db, user.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    try:
        db_user = user_crud.create_user(db, user)
        return UserResponse.model_validate(db_user)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/{user_uuid}", response_model=UserResponse)
async def get_user(user_uuid: str, db: Session = Depends(get_db)):
    """Получить пользователя по UUID"""
    from uuid import UUID
    try:
        user = user_crud.get_user_by_uuid(db, UUID(user_uuid))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return UserResponse.model_validate(user)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid UUID format"
        )

@router.get("/email/{email}", response_model=UserResponse)
async def get_user_by_email(email: str, db: Session = Depends(get_db)):
    """Получить пользователя по email"""
    user = user_crud.get_user_by_email(db, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return UserResponse.model_validate(user)

@router.get("/", response_model=UserListResponse)
async def get_all_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Получить всех пользователей"""
    users = user_crud.get_all_users(db, skip=skip, limit=limit)
    return UserListResponse(users=[UserResponse.model_validate(user) for user in users])

@router.put("/{user_uuid}", response_model=UserResponse)
async def update_user(
    user_uuid: str,
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Обновить пользователя (только для админов)"""
    from uuid import UUID
    try:
        user = user_crud.update_user(db, UUID(user_uuid), user_update)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return UserResponse.model_validate(user)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid UUID format"
        )

@router.put("/email/{email}", response_model=UserResponse)
async def update_user_by_email(
    email: str,
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Обновить пользователя по email (только свои данные)"""
    if current_user.get("email") != email and current_user.get("role") != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )

    user = user_crud.update_user_by_email(db, email, user_update)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return UserResponse.model_validate(user)

@router.post("/{user_uuid}/verify")
async def verify_user(user_uuid: str, db: Session = Depends(get_db)):
    """Подтвердить email пользователя"""
    from uuid import UUID
    try:
        user = user_crud.verify_user(db, UUID(user_uuid))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return {"message": "User verified successfully"}
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid UUID format"
        )

@router.put("/{user_uuid}/role", response_model=TokenResponse)
async def update_user_role(
    user_uuid: str,
    role_update: RoleUpdate,
    db: Session = Depends(get_db)
):
    """Изменить роль пользователя и вернуть новый JWT токен"""
    from uuid import UUID
    try:
        uuid_obj = UUID(user_uuid)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    user = user_crud.update_user_role(db, uuid_obj, role_update.role)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token_data = {
        "email": user.email,
        "role": user.role.value,
        "uuid": str(user.uuid)
    }

    access_token = create_access_token(token_data, access_token_expires)
    refresh_token = create_refresh_token(token_data)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user_uuid=str(user.uuid)
    )

