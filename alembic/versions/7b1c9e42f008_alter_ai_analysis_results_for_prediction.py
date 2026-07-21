"""alter ai_analysis_results for pneumonia prediction

heatmap_url  : NOT NULL -> NULL
    요구사항(REQ-PRED-001)상 Heatmap Image URL 은 선택사항이고,
    현재 사용하는 pneumonia_ensemble_v1 모델은 히트맵을 생성하지 않는다.

confidence   : Numeric(5,2) -> Numeric(5,4)
    모델이 반환하는 0.9821 이 소수점 2자리에서 0.98 로 잘려 정밀도가 손실된다.

Revision ID: 7b1c9e42f008
Revises: 03261c864267
Create Date: 2026-07-21 17:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7b1c9e42f008'
down_revision: Union[str, Sequence[str], None] = '03261c864267'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        'ai_analysis_results',
        'heatmap_url',
        existing_type=sa.String(length=255),
        nullable=True,
    )
    op.alter_column(
        'ai_analysis_results',
        'confidence',
        existing_type=sa.Numeric(precision=5, scale=2),
        type_=sa.Numeric(precision=5, scale=4),
        existing_nullable=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    # NULL 인 행이 있으면 NOT NULL 로 되돌릴 수 없으므로 먼저 빈 문자열로 채운다.
    op.execute(
        "UPDATE ai_analysis_results SET heatmap_url = '' WHERE heatmap_url IS NULL"
    )
    op.alter_column(
        'ai_analysis_results',
        'confidence',
        existing_type=sa.Numeric(precision=5, scale=4),
        type_=sa.Numeric(precision=5, scale=2),
        existing_nullable=False,
    )
    op.alter_column(
        'ai_analysis_results',
        'heatmap_url',
        existing_type=sa.String(length=255),
        nullable=False,
    )
