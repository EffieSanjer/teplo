"""Separate surprise lists for confirmed friends of each recipient."""

import sqlalchemy as sa
from alembic import op

revision = "d6f810b3c927"
down_revision = "c4e7290d61af"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "friend_surprise_spaces",
        sa.Column("recipient_id", sa.String(36), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("community_id", sa.String(36), sa.ForeignKey("communities.id"), nullable=False, unique=True),
    )


def downgrade():
    op.drop_table("friend_surprise_spaces")
