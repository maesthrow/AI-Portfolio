"""add project fields to experience"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
# Keep revision id short enough for alembic_version.version_num (VARCHAR(32)).
revision = "0002_add_project_fields"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("experience", sa.Column("project_name", sa.String(length=200), nullable=True))
    op.add_column("experience", sa.Column("project_slug", sa.String(length=100), nullable=True))
    op.add_column("experience", sa.Column("project_url", sa.String(length=255), nullable=True))
    op.add_column("experience", sa.Column("summary_md", sa.Text(), nullable=True))
    op.add_column("experience", sa.Column("achievements_md", sa.Text(), nullable=True))

    op.alter_column("experience", "company_name", existing_type=sa.String(), nullable=True)
    op.alter_column("experience", "description_md", existing_type=sa.Text(), nullable=True)


def downgrade() -> None:
    op.alter_column("experience", "description_md", existing_type=sa.Text(), nullable=False)
    op.alter_column("experience", "company_name", existing_type=sa.String(), nullable=False)

    op.drop_column("experience", "achievements_md")
    op.drop_column("experience", "summary_md")
    op.drop_column("experience", "project_url")
    op.drop_column("experience", "project_slug")
    op.drop_column("experience", "project_name")
