"""update project for personal/commercial: kind, weight, repo_url, demo_url

Revision ID: a8179a656e45
Revises: 1d7fa8a34aa4
Create Date: 2025-11-09 13:06:28.318328
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "a8179a656e45"
down_revision: Union[str, Sequence[str], None] = "1d7fa8a34aa4"
branch_labels = None
depends_on = None

project_kind = sa.Enum("COMMERCIAL", "PERSONAL", name="project_kind")


def upgrade() -> None:
    bind = op.get_bind()
    project_kind.create(bind, checkfirst=True)

    with op.batch_alter_table("projects", schema=None) as batch_op:
        # делаем company_id nullable + меняем FK на SET NULL
        batch_op.alter_column("company_id", existing_type=sa.Integer(), nullable=True)
        # если имя FK неизвестно/генерилось — безопаснее сначала дропнуть любой FK на company_id:
        # (если знаешь точное имя, можешь дропнуть по имени)
        try:
            batch_op.drop_constraint("projects_company_id_fkey", type_="foreignkey")
        except Exception:
            pass
        batch_op.create_foreign_key(None, "companies", ["company_id"], ["id"], ondelete="SET NULL")

        # новые колонки с временными дефолтами, чтобы не упасть на непустой таблице
        batch_op.add_column(sa.Column("kind", project_kind, nullable=True, server_default="COMMERCIAL"))
        batch_op.add_column(sa.Column("weight", sa.Integer(), nullable=True, server_default="100"))
        batch_op.add_column(sa.Column("repo_url", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("demo_url", sa.String(length=255), nullable=True))

    # ------ ВАЖНО: enum-литералы с кастом ------
    op.execute("""
        UPDATE projects
        SET kind = CASE
            WHEN company_id IS NULL THEN 'PERSONAL'::project_kind
            ELSE 'COMMERCIAL'::project_kind
        END
    """)

    # при необходимости расставляем веса (не 0; оставим 100/200 как пример приоритета)
    op.execute("""
        UPDATE projects
        SET weight = CASE
            WHEN company_id IS NULL THEN 200
            ELSE 100
        END
        WHERE weight IS NULL
    """)

    # ужесточаем NOT NULL и убираем server_default
    with op.batch_alter_table("projects", schema=None) as batch_op:
        batch_op.alter_column("kind", nullable=False, server_default=None)
        batch_op.alter_column("weight", nullable=False, server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("projects", schema=None) as batch_op:
        batch_op.drop_constraint(None, type_="foreignkey")
        batch_op.create_foreign_key("projects_company_id_fkey", "companies", ["company_id"], ["id"], ondelete="CASCADE")
        batch_op.alter_column("company_id", existing_type=sa.Integer(), nullable=False)

        batch_op.drop_column("demo_url")
        batch_op.drop_column("repo_url")
        batch_op.drop_column("weight")
        batch_op.drop_column("kind")

    bind = op.get_bind()
    project_kind.drop(bind, checkfirst=True)