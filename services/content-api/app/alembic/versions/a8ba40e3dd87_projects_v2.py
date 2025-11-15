"""projects_v2

Revision ID: a8ba40e3dd87
Revises: 7f199b36b47b
Create Date: 2025-11-04 09:42:26.848341

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'a8ba40e3dd87'
down_revision: Union[str, Sequence[str], None] = '7f199b36b47b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # --- projects: rename columns
    with op.batch_alter_table("projects") as b:
        # если столбцов нет/уже переименованы — просто проигнорируй на dev
        try:
            b.alter_column("title", new_column_name="name")
        except Exception:
            pass
        try:
            b.alter_column("summary", new_column_name="description")
        except Exception:
            pass

    # --- projects.tags: привести к массиву строк
    conn = op.get_bind()
    # Временная колонка
    op.add_column("projects", sa.Column("tags2", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False))

    # Если tags — объект флагов -> массив ключей со значением true.
    conn.execute(sa.text("""
        UPDATE projects
        SET tags2 = CASE
            WHEN jsonb_typeof(tags) = 'object' THEN (
                SELECT COALESCE(jsonb_agg(key), '[]'::jsonb)
                FROM jsonb_each(tags)
                WHERE value = 'true'::jsonb
            )
            WHEN jsonb_typeof(tags) = 'array' THEN tags
            ELSE '[]'::jsonb
        END
        WHERE tags IS NOT NULL;
    """))

    # Заменяем
    with op.batch_alter_table("projects") as b:
        try:
            b.drop_column("tags")
        except Exception:
            pass
        b.alter_column("tags2", new_column_name="tags")

    # Индекс GIN
    op.execute("CREATE INDEX IF NOT EXISTS idx_projects_tags_gin ON projects USING GIN (tags jsonb_path_ops)")

    # --- achievements: link -> links (jsonb[])
    op.add_column("achievements", sa.Column("links", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False))

    conn.execute(sa.text("""
        UPDATE achievements
        SET links = CASE
            WHEN link IS NULL OR link = '' THEN '[]'::jsonb
            ELSE jsonb_build_array(link)
        END
        WHERE links = '[]'::jsonb OR links IS NULL;
    """))

    with op.batch_alter_table("achievements") as b:
        try:
            b.drop_column("link")
        except Exception:
            pass

    # --- technologies + m2m
    op.create_table(
        "technologies",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=120), nullable=False, unique=True),
        sa.Column("description", sa.Text()),
    )

    op.create_table(
        "project_technologies",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("technology_id", sa.Integer(), sa.ForeignKey("technologies.id", ondelete="CASCADE"), nullable=False, index=True),
    )
    op.create_unique_constraint("uq_project_technology", "project_technologies", ["project_id", "technology_id"])


def downgrade():
    # откат по минимуму
    op.drop_constraint("uq_project_technology", "project_technologies", type_="unique")
    op.drop_table("project_technologies")
    op.drop_table("technologies")

    with op.batch_alter_table("achievements") as b:
        b.add_column(sa.Column("link", sa.String(length=255)))
    op.execute("""
        UPDATE achievements
        SET link = COALESCE(links->>0, NULL)
    """)
    with op.batch_alter_table("achievements") as b:
        b.drop_column("links")

    # projects.tags назад в объект (упрощённо)
    op.add_column("projects", sa.Column("tags_old", postgresql.JSONB(astext_type=sa.Text())))
    op.execute("""
        UPDATE projects
        SET tags_old = (
            SELECT COALESCE(
                jsonb_object_agg(value, true),
                '{}'::jsonb
            )
            FROM jsonb_array_elements_text(tags)
        )
    """)
    with op.batch_alter_table("projects") as b:
        b.drop_column("tags")
        b.alter_column("tags_old", new_column_name="tags")

    with op.batch_alter_table("projects") as b:
        b.alter_column("name", new_column_name="title")
        b.alter_column("description", new_column_name="summary")

    op.execute("DROP INDEX IF EXISTS idx_projects_tags_gin")
