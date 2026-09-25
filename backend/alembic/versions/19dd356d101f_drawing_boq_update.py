"""drawing_boq update

Revision ID: 19dd356d101f
Revises: fb7a2d428faa
Create Date: 2026-09-24 05:53:15.281082
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '19dd356d101f'
down_revision: Union[str, Sequence[str], None] = 'fb7a2d428faa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.alter_column(
        'drawings',
        'revision_label',
        existing_type=sa.VARCHAR(length=50),
        type_=sa.String(length=100),
        existing_nullable=True,
    )
    op.drop_index(op.f('ix_drawings_revision_group'), table_name='drawings')
    op.create_index(
        op.f('ix_drawings_revision_group_id'),
        'drawings',
        ['revision_group_id'],
        unique=False,
    )
    # Only drop the FK if you intentionally no longer want revision_group_id
    # to reference drawings.id. If you still want that FK, leave this out.
    op.drop_constraint(op.f('fk_drawings_revision_group'), 'drawings', type_='foreignkey')


def downgrade() -> None:
    op.create_foreign_key(
        op.f('fk_drawings_revision_group'),
        'drawings', 'drawings',
        ['revision_group_id'], ['id'],
        ondelete='RESTRICT',
    )
    op.drop_index(op.f('ix_drawings_revision_group_id'), table_name='drawings')
    op.create_index(
        op.f('ix_drawings_revision_group'),
        'drawings',
        ['revision_group_id'],
        unique=False,
    )
    op.alter_column(
        'drawings',
        'revision_label',
        existing_type=sa.String(length=100),
        type_=sa.VARCHAR(length=50),
        existing_nullable=True,
    )