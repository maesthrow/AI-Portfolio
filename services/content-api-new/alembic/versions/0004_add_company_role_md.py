"""add company_role_md to experience"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0004_add_company_role_md"
down_revision = "0003_company_experience_projects"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("experience", sa.Column("company_role_md", sa.Text(), nullable=True))

    # Backfill from existing summary_md to keep current descriptions visible
    op.execute("UPDATE experience SET company_role_md = summary_md WHERE company_role_md IS NULL")


def downgrade() -> None:
    op.drop_column("experience", "company_role_md")
