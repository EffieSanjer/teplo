"""Mutual friendships and hashed single-use invitations; preserve existing data."""

import sqlalchemy as sa
from alembic import op

revision = "c4e7290d61af"
down_revision = "b8d92a41e760"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "friendships",
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("friend_id", sa.String(36), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("user_id < friend_id", name="friendship_order"),
    )
    op.create_index("ix_friendships_friend_id", "friendships", ["friend_id"])
    op.create_table(
        "friend_invitations",
        sa.Column("token_hash", sa.String(64), primary_key=True),
        sa.Column("owner_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("accepted_by", sa.String(36), sa.ForeignKey("users.id")),
    )
    op.create_index("ix_friend_invitations_owner_id", "friend_invitations", ["owner_id"])


def downgrade():
    op.drop_table("friend_invitations")
    op.drop_table("friendships")
