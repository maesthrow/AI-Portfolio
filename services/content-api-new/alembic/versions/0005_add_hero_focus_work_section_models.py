"""add hero_tag, focus_area, work_approach, section_meta models and profile hero fields"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0005_add_content_models"
down_revision = "0004_add_company_role_md"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns to profile table
    op.add_column("profile", sa.Column("hero_headline", sa.String(), nullable=True))
    op.add_column("profile", sa.Column("hero_description", sa.Text(), nullable=True))
    op.add_column("profile", sa.Column("current_position", sa.String(), nullable=True))

    # Create hero_tag table
    op.create_table(
        "hero_tag",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("url", sa.String(), nullable=True),
        sa.Column("icon", sa.String(), nullable=True),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create focus_area table
    op.create_table(
        "focus_area",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create focus_area_bullet table
    op.create_table(
        "focus_area_bullet",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("focus_area_id", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["focus_area_id"], ["focus_area.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create work_approach table
    op.create_table(
        "work_approach",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create work_approach_bullet table
    op.create_table(
        "work_approach_bullet",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("work_approach_id", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["work_approach_id"], ["work_approach.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create section_meta table
    op.create_table(
        "section_meta",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("section_key", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("subtitle", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("section_key"),
    )
    op.create_index("ix_section_meta_section_key", "section_meta", ["section_key"])


def downgrade() -> None:
    op.drop_index("ix_section_meta_section_key", "section_meta")
    op.drop_table("section_meta")
    op.drop_table("work_approach_bullet")
    op.drop_table("work_approach")
    op.drop_table("focus_area_bullet")
    op.drop_table("focus_area")
    op.drop_table("hero_tag")
    op.drop_column("profile", "current_position")
    op.drop_column("profile", "hero_description")
    op.drop_column("profile", "hero_headline")
