from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import httpx
from app.schemas.auth import UserCreate, UserLogin, UserUpdate, UserResponse, UserListResponse, RoleUpdate, TokenResponse, RefreshTokenRequest
from app.services.auth_service import AuthService
from app.core.config import get_settings

router = APIRouter()
security = HTTPBearer()
settings = get_settings()

auth_service = AuthService()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Получить текущего пользователя из JWT токена"""

    # В локальном режиме пропускаем валидацию токена
    if settings.BACKEND_LOCAL:
        return {
            "email": "local@user.com",
            "role": "ADMIN",
            "uuid": "00000000-0000-0000-0000-000000000001"
        }

    try:
        payload = auth_service.decode_token(credentials.credentials)
        return payload
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Получить данные текущего пользователя"""

    # В локальном режиме возвращаем захардкоженного пользователя
    if settings.BACKEND_LOCAL:
        return UserResponse(
            uuid=current_user["uuid"],
            email=current_user["email"],
            role=current_user["role"]
        )

    try:
        user = await auth_service.get_user_by_email(current_user["email"])
        return UserResponse(
            uuid=user["uuid"],
            email=user["email"],
            role=user.get("role", "USER")
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

@router.get("/user/{user_id}", response_model=UserResponse)
async def get_user_by_id(user_id: str, current_user: dict = Depends(get_current_user)):
    """Получить данные пользователя по UUID"""
    try:
        user = await auth_service.get_user_by_id(user_id)
        return UserResponse(
            uuid=user["uuid"],
            email=user["email"],
            role=user.get("role", "USER")
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

@router.get("/users", response_model=UserListResponse)
async def get_all_users(current_user: dict = Depends(get_current_user)):
    """Получить всех пользователей (только для админов)"""
    if current_user.get("role") != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )

    try:
        response = await auth_service.get_all_users()
        users = response.get("users", [])
        return UserListResponse(users=users)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get users"
        )

@router.post("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Обновить данные текущего пользователя"""
    try:
        updated_user = await auth_service.update_user(
            current_user["email"],
            user_update.dict(exclude_unset=True)
        )
        return UserResponse(
            uuid=updated_user["uuid"],
            email=updated_user["email"]
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update user"
        )

@router.post("/create", response_model=dict)
async def create_user(user_data: UserCreate):
    """Создать нового пользователя"""
    try:
        if user_data.password != user_data.confirm_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Passwords do not match"
            )

        user = await auth_service.create_user(user_data.dict())
        return {"message": "User created successfully", "uuid": user["uuid"]}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/login", response_model=TokenResponse)
async def login_user(user_credentials: UserLogin):
    """Войти в систему"""
    try:
        result = await auth_service.authenticate_user(
            user_credentials.email,
            user_credentials.password
        )
        return TokenResponse(**result)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(token_request: RefreshTokenRequest):
    """Обновить access токен используя refresh токен"""
    try:
        result = await auth_service.refresh_access_token(token_request.refresh_token)
        return TokenResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )

@router.post("/logout")
async def logout(token_request: RefreshTokenRequest):
    """Выйти из системы (отозвать refresh токен)"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.AUTH_SERVICE_URL}/auth/logout",
                json={"refresh_token": token_request.refresh_token}
            )
            response.raise_for_status()
            return {"message": "Successfully logged out"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to logout"
        )

@router.put("/user/{user_uuid}/role", response_model=TokenResponse)
async def update_user_role(
    user_uuid: str,
    role_data: RoleUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Изменить роль пользователя (только для админов)"""
    try:
        user = await auth_service.update_user_role(user_uuid, role_data.role)
        return user
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

