"""add route_name to analysis_tasks

Revision ID: 001
Revises: 
Create Date: 2025-11-20 12:00:00.000000

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
    """Add route_name column to analysis_tasks table."""
    op.add_column(
        'analysis_tasks',
        sa.Column('route_name', sa.String(length=250), nullable=True)
    )
    
    # Добавляем комментарий к колонке
    op.execute(
        "COMMENT ON COLUMN analysis_tasks.route_name IS "
        "'Название маршрута для задачи анализа (до 250 символов)'"
    )


def downgrade() -> None:
    """Remove route_name column from analysis_tasks table."""
    op.drop_column('analysis_tasks', 'route_name')

