import httpx
from typing import Dict, Any, Optional, List
from fastapi import HTTPException, status, UploadFile
from app.core.config import get_settings

settings = get_settings()

class FilesService:
    def __init__(self):
        self.files_service_url = settings.FILES_SERVICE_URL
        self.timeout = 30.0

    async def upload_file(
        self,
        file: UploadFile,
        project_id: str,
        file_type: str,
        uploaded_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """Загрузить файл через files-service"""
        try:
            files = {
                "file": (file.filename, file.file, file.content_type)
            }
            data = {
                "project_id": project_id,
                "file_type": file_type,
            }
            if uploaded_by:
                data["uploaded_by"] = uploaded_by

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.files_service_url}/files/upload",
                    files=files,
                    data=data
                )

                if response.status_code == 413:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="File size exceeds maximum allowed size"
                    )
                elif response.status_code == 400:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=response.json().get("detail", "Bad request")
                    )

                response.raise_for_status()
                return response.json()

        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Files service error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Cannot connect to files service: {str(e)}"
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload file: {str(e)}"
            )

    async def upload_bytes(
        self,
        *,
        data: bytes,
        filename: str,
        content_type: str,
        project_id: str,
        file_type: str,
        uploaded_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Загрузить файл из байтового буфера."""
        try:
            files = {
                "file": (filename, data, content_type),
            }
            payload = {
                "project_id": project_id,
                "file_type": file_type,
            }
            if uploaded_by:
                payload["uploaded_by"] = uploaded_by

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.files_service_url}/files/upload",
                    files=files,
                    data=payload,
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Files service error: {e.response.text}",
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Cannot connect to files service: {str(e)}",
            )

    async def batch_upload_files(
        self,
        files: List[UploadFile],
        project_id: str,
        file_type: str,
        uploaded_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """Загрузить массив файлов через files-service за один запрос"""
        try:
            # Подготавливаем files для multipart/form-data
            files_data = []
            for file in files:
                file.file.seek(0)
                files_data.append(
                    ("files", (file.filename, file.file, file.content_type))
                )
            
            data = {
                "project_id": project_id,
                "file_type": file_type,
            }
            if uploaded_by:
                data["uploaded_by"] = uploaded_by

            async with httpx.AsyncClient(timeout=60.0) as client:  # Увеличенный таймаут для batch
                response = await client.post(
                    f"{self.files_service_url}/files/batch-upload",
                    files=files_data,
                    data=data
                )

                if response.status_code == 413:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="Total file size exceeds maximum allowed size"
                    )
                elif response.status_code == 400:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=response.json().get("detail", "Bad request")
                    )

                response.raise_for_status()
                return response.json()

        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Files service error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Cannot connect to files service: {str(e)}"
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to batch upload files: {str(e)}"
            )

    async def batch_upload_bytes(
        self,
        files_data: List[Dict[str, Any]],  # [{"data": bytes, "filename": str, "content_type": str}, ...]
        project_id: str,
        file_type: str,
        uploaded_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Загрузить массив файлов из байтов через files-service за один запрос"""
        try:
            # Подготавливаем files для multipart/form-data
            files = []
            for file_info in files_data:
                files.append(
                    ("files", (file_info["filename"], file_info["data"], file_info["content_type"]))
                )
            
            payload = {
                "project_id": project_id,
                "file_type": file_type,
            }
            if uploaded_by:
                payload["uploaded_by"] = uploaded_by

            async with httpx.AsyncClient(timeout=60.0) as client:  # Увеличенный таймаут для batch
                response = await client.post(
                    f"{self.files_service_url}/files/batch-upload",
                    files=files,
                    data=payload,
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Files service error: {e.response.text}",
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Cannot connect to files service: {str(e)}",
            )

    async def download_file(self, file_id: str) -> bytes:
        """Скачать файл через files-service"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.files_service_url}/files/{file_id}/download"
                )

                if response.status_code == 404:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="File not found"
                    )

                response.raise_for_status()
                return response.content

        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Files service error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Cannot connect to files service: {str(e)}"
            )
        except HTTPException:
            raise

    async def batch_download_files(self, file_ids: List[str]) -> Dict[str, Any]:
        """Скачать массив файлов через files-service за один запрос"""
        import base64
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:  # Увеличенный таймаут для batch
                response = await client.post(
                    f"{self.files_service_url}/files/batch-download",
                    json={"file_ids": file_ids}
                )

                if response.status_code == 404:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Some files not found"
                    )

                response.raise_for_status()
                result = response.json()
                
                # Декодируем base64 обратно в bytes
                for file_data in result.get("files", []):
                    if "content" in file_data and isinstance(file_data["content"], str):
                        file_data["content"] = base64.b64decode(file_data["content"])
                
                return result

        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Files service error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Cannot connect to files service: {str(e)}"
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to batch download files: {str(e)}"
            )

    async def get_file_metadata(self, file_id: str) -> Dict[str, Any]:
        """Получить метаданные файла через files-service"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.files_service_url}/files/{file_id}"
                )

                if response.status_code == 404:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="File not found"
                    )

                response.raise_for_status()
                return response.json()

        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Files service error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Cannot connect to files service: {str(e)}"
            )
        except HTTPException:
            raise

    async def get_project_files(self, project_id: str) -> list:
        """Получить все файлы проекта через files-service"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.files_service_url}/files/project/{project_id}"
                )
                response.raise_for_status()
                result = response.json()
                return result.get("files", [])

        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Files service error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Cannot connect to files service: {str(e)}"
            )

    async def delete_file(self, file_id: str) -> bool:
        """Удалить файл через files-service"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{self.files_service_url}/files/{file_id}"
                )

                if response.status_code == 404:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="File not found"
                    )

                response.raise_for_status()
                return True

        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Files service error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Cannot connect to files service: {str(e)}"
            )
        except HTTPException:
            raise

