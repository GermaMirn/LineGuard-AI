import os
import hashlib
import shutil
from pathlib import Path
from typing import BinaryIO, Tuple
from uuid import UUID
from fastapi import UploadFile, HTTPException, status
from app.core.config import get_settings

settings = get_settings()

class StorageService:
    def __init__(self):
        self.storage_path = Path(settings.STORAGE_PATH)
        self.max_file_size = settings.MAX_FILE_SIZE

    def _ensure_project_directory(self, project_id: UUID) -> Path:
        """Создать директорию для проекта если её нет"""
        project_dir = self.storage_path / str(project_id)
        project_dir.mkdir(parents=True, exist_ok=True)
        return project_dir

    def _calculate_checksum(self, file_path: Path) -> str:
        """Вычислить MD5 хэш файла"""
        md5_hash = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                md5_hash.update(chunk)
        return md5_hash.hexdigest()

    def _validate_file_size(self, file: UploadFile) -> None:
        """Проверить размер файла"""
        file.file.seek(0, 2)
        file_size = file.file.tell()
        file.file.seek(0)

        if file_size > self.max_file_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size exceeds maximum allowed size of {self.max_file_size} bytes"
            )

    def _validate_file_extension(self, filename: str, file_type: str) -> None:
        """Проверить расширение файла"""
        file_ext = Path(filename).suffix.lower()

        allowed_extensions = {
            "JSON_SCHEMA": settings.ALLOWED_JSON_EXTENSIONS,
            "XSD_SCHEMA": settings.ALLOWED_XSD_EXTENSIONS,
            "TEST_DATA": settings.ALLOWED_TEST_DATA_EXTENSIONS,
            "VM_TEMPLATE": settings.ALLOWED_VM_EXTENSIONS,
            "IMAGE": settings.ALLOWED_IMAGE_EXTENSIONS,
        }

        if file_ext not in allowed_extensions.get(file_type, set()):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file extension '{file_ext}' for file type {file_type}"
            )

    async def save_file(
        self,
        file: UploadFile,
        project_id: UUID,
        file_type: str,
        file_id: UUID
    ) -> Tuple[str, int, str]:
        """Сохранить файл на диск"""
        self._validate_file_size(file)
        self._validate_file_extension(file.filename, file_type)

        project_dir = self._ensure_project_directory(project_id)

        file_extension = Path(file.filename).suffix
        unique_filename = f"{file_id}{file_extension}"
        file_path = project_dir / unique_filename

        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save file: {str(e)}"
            )

        file_size = file_path.stat().st_size
        checksum = self._calculate_checksum(file_path)

        return str(file_path), file_size, checksum

    def get_file_path(self, file_path_str: str) -> Path:
        """Получить Path объект для файла"""
        file_path = Path(file_path_str)

        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found on disk"
            )

        return file_path

    def delete_file(self, file_path_str: str) -> bool:
        """Удалить файл с диска"""
        try:
            file_path = Path(file_path_str)
            if file_path.exists():
                file_path.unlink()
                return True
            return False
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete file: {str(e)}"
            )

    def read_file_content(self, file_path_str: str) -> bytes:
        """Прочитать содержимое файла"""
        file_path = self.get_file_path(file_path_str)

        try:
            with open(file_path, "rb") as f:
                return f.read()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to read file: {str(e)}"
            )

