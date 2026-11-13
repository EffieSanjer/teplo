"""Separate personal Telegram workspaces from group and demo communities."""

import sqlalchemy as sa
from alembic import op

revision = "b8d92a41e760"
down_revision = "97bc42d8a610"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "personal_workspaces",
        sa.Column("community_id", sa.String(36), sa.ForeignKey("communities.id"), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False, unique=True),
    )


def downgrade():
    op.drop_table("personal_workspaces")
