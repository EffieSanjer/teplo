"""Allow exact prices alongside approximate and minimum prices."""

import sqlalchemy as sa
from alembic import op

revision = "a5c034eb26df"
down_revision = "f4b923da15ce"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("items") as batch:
        batch.drop_constraint("item_price_mode", type_="check")
        batch.alter_column("price_mode", existing_type=sa.String(16), server_default="exact")
        batch.create_check_constraint("item_price_mode", "price_mode IN ('exact', 'approximate', 'from')")


def downgrade():
    connection = op.get_bind()
    if connection.scalar(sa.text("SELECT count(*) FROM items WHERE price_mode = 'exact'")):
        raise RuntimeError("Convert exact prices before downgrading")
    with op.batch_alter_table("items") as batch:
        batch.drop_constraint("item_price_mode", type_="check")
        batch.alter_column("price_mode", existing_type=sa.String(16), server_default="approximate")
        batch.create_check_constraint("item_price_mode", "price_mode IN ('approximate', 'from')")
