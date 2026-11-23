"""Gift reservations and private surprises."""

import sqlalchemy as sa
from alembic import op

revision = "e3a812c904bd"
down_revision = "d6f810b3c927"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("items", sa.Column("surprise_visibility", sa.String(10), nullable=False, server_default="friends"))
    op.create_check_constraint("item_surprise_visibility", "items", "surprise_visibility IN ('friends', 'private')")
    op.create_table(
        "item_reservations",
        sa.Column("item_id", sa.String(36), sa.ForeignKey("items.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )


def downgrade():
    op.drop_table("item_reservations")
    op.drop_constraint("item_surprise_visibility", "items", type_="check")
    op.drop_column("items", "surprise_visibility")
