import httpx
import jwt
from typing import Dict, Any
from fastapi import HTTPException, status
from app.core.config import get_settings

settings = get_settings()

class AuthService:
    def __init__(self):
        self.auth_service_url = settings.AUTH_SERVICE_URL
        self.secret_key = settings.SECRET_KEY
        self.algorithm = settings.ALGORITHM

    async def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Создать пользователя через auth-service"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.auth_service_url}/users/",
                json=user_data
            )
            response.raise_for_status()
            return response.json()

    async def authenticate_user(self, email: str, password: str) -> Dict[str, Any]:
        """Аутентификация пользователя через auth-service"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.auth_service_url}/auth/login",
                json={"email": email, "password": password}
            )
            response.raise_for_status()
            return response.json()

    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Обновить access токен через auth-service"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.auth_service_url}/auth/refresh",
                json={"refresh_token": refresh_token}
            )
            if response.status_code == 401:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired refresh token"
                )
            response.raise_for_status()
            return response.json()

    async def get_user_by_email(self, email: str) -> Dict[str, Any]:
        """Получить пользователя по email через auth-service"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.auth_service_url}/users/email/{email}"
            )
            response.raise_for_status()
            return response.json()

    async def get_user_by_id(self, user_id: str) -> Dict[str, Any]:
        """Получить пользователя по ID через auth-service"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.auth_service_url}/users/{user_id}"
            )
            response.raise_for_status()
            return response.json()

    async def get_all_users(self) -> list[Dict[str, Any]]:
        """Получить всех пользователей через auth-service"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.auth_service_url}/users/"
            )
            response.raise_for_status()
            return response.json()

    async def update_user(self, email: str, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Обновить пользователя через auth-service"""
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{self.auth_service_url}/users/email/{email}",
                json=user_data
            )
            response.raise_for_status()
            return response.json()

    async def update_user_role(self, user_uuid: str, role) -> Dict[str, Any]:
        """Изменить роль пользователя через auth-service"""
        async with httpx.AsyncClient() as client:
            role_value = role.value if hasattr(role, 'value') else str(role)
            response = await client.put(
                f"{self.auth_service_url}/users/{user_uuid}/role",
                json={"role": role_value}
            )

            if response.status_code == 404:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            elif response.status_code == 400:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid role"
                )

            response.raise_for_status()
            return response.json()

    def decode_token(self, token: str) -> Dict[str, Any]:
        """Декодировать JWT токен"""
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise Exception("Token has expired")
        except jwt.JWTError:
            raise Exception("Invalid token")

