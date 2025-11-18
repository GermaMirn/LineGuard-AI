from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.database import get_db
from app.schemas import UserLogin, TokenResponse, RefreshTokenRequest
from app.crud import user_crud, refresh_token_crud
from app.utils.auth import create_access_token, create_refresh_token, verify_token
from app.core.config import get_settings

router = APIRouter()
settings = get_settings()

@router.post("/login", response_model=TokenResponse)
async def login(user_credentials: UserLogin, db: Session = Depends(get_db)):
    """Войти в систему"""
    user = user_crud.authenticate_user(db, user_credentials.email, user_credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"email": user.email, "role": user.role.value, "uuid": str(user.uuid)},
        expires_delta=access_token_expires
    )

    refresh_token = create_refresh_token(
        data={"email": user.email, "uuid": str(user.uuid)}
    )

    refresh_token_expires = datetime.utcnow() + timedelta(days=7)
    refresh_token_crud.create_refresh_token(
        db, user.uuid, refresh_token, refresh_token_expires
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user_uuid=str(user.uuid)
    )

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(token_request: RefreshTokenRequest, db: Session = Depends(get_db)):
    """Обновить access токен"""
    db_token = refresh_token_crud.get_refresh_token(db, token_request.refresh_token)
    if not db_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    user = user_crud.get_user_by_uuid(db, db_token.user_uuid)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"email": user.email, "role": user.role.value, "uuid": str(user.uuid)},
        expires_delta=access_token_expires
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=token_request.refresh_token,  # Возвращаем тот же refresh токен
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user_uuid=str(user.uuid)
    )

@router.post("/logout")
async def logout(token_request: RefreshTokenRequest, db: Session = Depends(get_db)):
    """Выйти из системы"""
    success = refresh_token_crud.revoke_token(db, token_request.refresh_token)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid refresh token"
        )

    return {"message": "Successfully logged out"}

