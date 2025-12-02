"""introduce company slug and experience projects"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
from sqlalchemy import Integer, String, Text, Date, Boolean
from datetime import datetime
import re

# revision identifiers, used by Alembic.
revision = "0003_company_experience_projects"
down_revision = "0002_add_project_fields"
branch_labels = None
depends_on = None


def slugify(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-+", "-", value)
    return value.strip("-") or "company"


def format_period(start_date, end_date, is_current):
    if not start_date:
        return None
    start_year = start_date.year
    if is_current or end_date is None:
        return f"{start_year} — н.в."
    return f"{start_year} — {end_date.year}"


def upgrade() -> None:
    # Add new columns to experience
    op.add_column("experience", sa.Column("company_slug", sa.String(), nullable=True))
    op.add_column("experience", sa.Column("company_summary_md", sa.Text(), nullable=True))
    op.create_unique_constraint("uq_experience_company_slug", "experience", ["company_slug"])

    # Create experience_project table
    op.create_table(
        "experience_project",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("experience_id", sa.Integer(), sa.ForeignKey("experience.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("period", sa.String(), nullable=True),
        sa.Column("description_md", sa.Text(), nullable=False),
        sa.Column("achievements_md", sa.Text(), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.UniqueConstraint("experience_id", "slug", name="uq_experience_project_slug"),
    )

    # Data migration
    conn = op.get_bind()
    experience_tbl = table(
        "experience",
        column("id", Integer),
        column("company_name", String),
        column("project_name", String),
        column("project_slug", String),
        column("summary_md", Text),
        column("achievements_md", Text),
        column("start_date", Date),
        column("end_date", Date),
        column("is_current", Boolean),
        column("company_slug", String),
        column("company_summary_md", Text),
        column("kind", String),
    )

    rows = conn.execute(sa.select(experience_tbl)).mappings().all()

    used_company_slugs = set()

    for row in rows:
        company_slug = row["company_slug"]
        if not company_slug:
            base = row["company_name"] or row["project_name"] or "company"
            company_slug = slugify(base)
        original_slug = company_slug
        counter = 1
        while company_slug in used_company_slugs:
            company_slug = f"{original_slug}-{counter}"
            counter += 1
        used_company_slugs.add(company_slug)
        conn.execute(
            experience_tbl.update()
            .where(experience_tbl.c.id == row["id"])
            .values(company_slug=company_slug, company_summary_md=row["summary_md"])
        )

        project_name = row["project_name"] or (row["company_name"] or "Проект")
        project_slug = row["project_slug"] or slugify(project_name)
        period = format_period(row["start_date"], row["end_date"], row["is_current"])
        description_md = row["summary_md"] or (row["company_name"] or project_name)
        achievements_md = row["achievements_md"] or ""

        conn.execute(
            sa.text(
                """
                INSERT INTO experience_project (
                    experience_id, name, slug, period, description_md, achievements_md, order_index, created_at, updated_at
                )
                VALUES (:experience_id, :name, :slug, :period, :description_md, :achievements_md, :order_index, :created_at, :updated_at)
                """
            ),
            {
                "experience_id": row["id"],
                "name": project_name,
                "slug": project_slug,
                "period": period,
                "description_md": description_md,
                "achievements_md": achievements_md,
                "order_index": 10,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            },
        )

    # Ensure company_slug is not null
    op.alter_column("experience", "company_slug", existing_type=sa.String(), nullable=False)


def downgrade() -> None:
    op.drop_table("experience_project")
    op.drop_constraint("uq_experience_company_slug", "experience", type_="unique")
    op.drop_column("experience", "company_summary_md")
    op.drop_column("experience", "company_slug")
