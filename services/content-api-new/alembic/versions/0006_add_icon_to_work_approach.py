"""add icon field to work_approach table"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0006_add_icon_to_work_approach"
down_revision = "0005_add_content_models"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("work_approach", sa.Column("icon", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("work_approach", "icon")
