"""Add ticket item type for event gifts outside known desks.

Revision ID: b7e1c4a92f03
Revises: a5c034eb26df
"""

import sqlalchemy as sa
from alembic import op

revision = "b7e1c4a92f03"
down_revision = "a5c034eb26df"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("items") as batch:
        batch.drop_constraint("item_type", type_="check")
        batch.create_check_constraint(
            "item_type", "item_type IN ('idea', 'gift', 'certificate', 'ticket')"
        )
        batch.create_check_constraint(
            "ticket_url", "item_type <> 'ticket' OR url IS NOT NULL AND length(url) > 0"
        )


def downgrade():
    connection = op.get_bind()
    if connection.scalar(sa.text("SELECT count(*) FROM items WHERE item_type = 'ticket'")):
        raise RuntimeError("Convert ticket entries before downgrading")
    with op.batch_alter_table("items") as batch:
        batch.drop_constraint("ticket_url", type_="check")
        batch.drop_constraint("item_type", type_="check")
        batch.create_check_constraint(
            "item_type", "item_type IN ('idea', 'gift', 'certificate')"
        )
