"""add analysis file types

Revision ID: 001
Revises: 
Create Date: 2025-11-18 14:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Сначала проверяем существование enum и создаем его, если нужно
    # Затем добавляем новые значения
    op.execute("""
        DO $$ 
        BEGIN
            -- Проверяем существование enum типа
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'filetype') THEN
                -- Создаем enum со всеми базовыми значениями
                CREATE TYPE filetype AS ENUM (
                    'JSON_SCHEMA',
                    'XSD_SCHEMA',
                    'TEST_DATA',
                    'VM_TEMPLATE',
                    'IMAGE',
                    'ANALYSIS_ORIGINAL',
                    'ANALYSIS_PREVIEW',
                    'ANALYSIS_RESULT',
                    'ANALYSIS_ARCHIVE'
                );
            ELSE
                -- Enum уже существует, добавляем только новые значения
                IF NOT EXISTS (
                    SELECT 1 FROM pg_enum 
                    WHERE enumlabel = 'ANALYSIS_ORIGINAL' 
                    AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'filetype')
                ) THEN
                    ALTER TYPE filetype ADD VALUE 'ANALYSIS_ORIGINAL';
                END IF;
                
                IF NOT EXISTS (
                    SELECT 1 FROM pg_enum 
                    WHERE enumlabel = 'ANALYSIS_PREVIEW' 
                    AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'filetype')
                ) THEN
                    ALTER TYPE filetype ADD VALUE 'ANALYSIS_PREVIEW';
                END IF;
                
                IF NOT EXISTS (
                    SELECT 1 FROM pg_enum 
                    WHERE enumlabel = 'ANALYSIS_RESULT' 
                    AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'filetype')
                ) THEN
                    ALTER TYPE filetype ADD VALUE 'ANALYSIS_RESULT';
                END IF;
                
                IF NOT EXISTS (
                    SELECT 1 FROM pg_enum 
                    WHERE enumlabel = 'ANALYSIS_ARCHIVE' 
                    AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'filetype')
                ) THEN
                    ALTER TYPE filetype ADD VALUE 'ANALYSIS_ARCHIVE';
                END IF;
            END IF;
        END $$;
    """)


def downgrade() -> None:
    # PostgreSQL не поддерживает удаление значений из enum напрямую
    # Нужно пересоздать enum или оставить значения
    pass

