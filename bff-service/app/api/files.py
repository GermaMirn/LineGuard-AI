from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File, Form
from fastapi.responses import StreamingResponse, Response
import io
from app.schemas.files import FileUploadResponse, FileResponse, FileListResponse, FileType
from app.services.files_service import FilesService
from app.api.auth import get_current_user

router = APIRouter()
files_service = FilesService()

@router.post("/upload", response_model=FileUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    project_id: str = Form(...),
    file_type: str = Form(...),
    current_user: dict = Depends(get_current_user)
):
    """Загрузить файл в систему"""
    try:
        if file_type not in [ft.value for ft in FileType]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file_type. Must be one of: {[ft.value for ft in FileType]}"
            )

        user_id = current_user.get("uuid") or current_user.get("user_id")

        result = await files_service.upload_file(
            file=file,
            project_id=project_id,
            file_type=file_type,
            uploaded_by=user_id
        )

        return FileUploadResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file: {str(e)}"
        )

@router.get("/{file_id}/download")
async def download_file(
    file_id: str
):
    """Скачать файл по ID (без авторизации для результатов анализа)"""
    try:
        metadata = await files_service.get_file_metadata(file_id)
        file_content = await files_service.download_file(file_id)

        file_name = metadata.get("file_name", "file.zip")
        mime_type = metadata.get("mime_type", "application/zip")
        file_size = len(file_content)

        # Используем Response вместо StreamingResponse для лучшей совместимости с Safari
        # И добавляем все необходимые заголовки
        return Response(
            content=file_content,
            media_type=mime_type,
            headers={
                "Content-Disposition": f'attachment; filename="{file_name}"; filename*=UTF-8\'\'{file_name}',
                "Content-Type": mime_type,
                "Content-Length": str(file_size),
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to download file: {str(e)}"
        )


@router.get("/{file_id}/view")
async def view_file(
    file_id: str
):
    """Просмотреть файл (inline, для отображения в браузере)"""
    try:
        metadata = await files_service.get_file_metadata(file_id)
        file_content = await files_service.download_file(file_id)

        file_name = metadata.get("file_name", "file.jpg")
        mime_type = metadata.get("mime_type", "image/jpeg")
        file_size = len(file_content)

        # Используем inline для просмотра в браузере
        return Response(
            content=file_content,
            media_type=mime_type,
            headers={
                "Content-Disposition": f'inline; filename="{file_name}"; filename*=UTF-8\'\'{file_name}',
                "Content-Type": mime_type,
                "Content-Length": str(file_size),
                "Cache-Control": "public, max-age=3600",  # Кэшируем на 1 час
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to view file: {str(e)}"
        )

@router.get("/{file_id}", response_model=FileResponse)
async def get_file_metadata(
    file_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Получить метаданные файла"""
    try:
        result = await files_service.get_file_metadata(file_id)
        return FileResponse(**result)

    except HTTPException:
        raise

@router.get("/project/{project_id}", response_model=FileListResponse)
async def get_project_files(
    project_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Получить все файлы проекта"""
    try:
        files = await files_service.get_project_files(project_id)
        return FileListResponse(files=files, total=len(files))

    except HTTPException:
        raise

@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file(
    file_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Удалить файл"""
    try:
        await files_service.delete_file(file_id)
        return None

    except HTTPException:
        raise

