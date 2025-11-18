from sqlalchemy.orm import Session
from sqlalchemy import and_
from uuid import UUID
from typing import List, Optional
from app.models import File, FileType
from app.schemas import FileUploadResponse

def create_file(
    db: Session,
    file_id: UUID,
    project_id: UUID,
    file_name: str,
    file_type: FileType,
    file_path: str,
    file_size: int,
    mime_type: str,
    checksum: str,
    uploaded_by: Optional[UUID] = None
) -> File:
    """Создать запись о файле в БД"""
    db_file = File(
        id=file_id,
        project_id=project_id,
        file_name=file_name,
        file_type=file_type,
        file_path=file_path,
        file_size=file_size,
        mime_type=mime_type,
        checksum=checksum,
        uploaded_by=uploaded_by
    )
    db.add(db_file)
    db.commit()
    db.refresh(db_file)
    return db_file

def get_file_by_id(db: Session, file_id: UUID) -> Optional[File]:
    """Получить файл по ID"""
    return db.query(File).filter(File.id == file_id).first()

def get_files_by_project(
    db: Session,
    project_id: UUID,
    skip: int = 0,
    limit: Optional[int] = None
) -> List[File]:
    """Получить файлы проекта с пагинацией"""
    query = db.query(File).filter(File.project_id == project_id)

    if skip:
        query = query.offset(skip)

    if limit:
        query = query.limit(limit)

    return query.all()

def count_files_by_project(db: Session, project_id: UUID) -> int:
    """Подсчитать общее количество файлов проекта"""
    return db.query(File).filter(File.project_id == project_id).count()

def get_file_by_project_and_type(
    db: Session,
    project_id: UUID,
    file_type: FileType
) -> Optional[File]:
    """Получить файл проекта по типу"""
    return db.query(File).filter(
        and_(
            File.project_id == project_id,
            File.file_type == file_type
        )
    ).first()

def delete_file(db: Session, file_id: UUID) -> bool:
    """Удалить запись о файле из БД"""
    db_file = get_file_by_id(db, file_id)
    if db_file:
        db.delete(db_file)
        db.commit()
        return True
    return False

