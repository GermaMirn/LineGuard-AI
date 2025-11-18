from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File, Form
from fastapi.responses import StreamingResponse
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
    file_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Скачать файл по ID"""
    try:
        metadata = await files_service.get_file_metadata(file_id)
        file_content = await files_service.download_file(file_id)

        return StreamingResponse(
            io.BytesIO(file_content),
            media_type=metadata.get("mime_type", "application/octet-stream"),
            headers={
                "Content-Disposition": f'attachment; filename="{metadata.get("file_name")}"'
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to download file: {str(e)}"
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

