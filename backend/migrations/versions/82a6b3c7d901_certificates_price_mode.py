"""Certificate shops and minimum prices.

Revision ID: 82a6b3c7d901
Revises: 3ec4765b3953
"""

from alembic import op
import sqlalchemy as sa

revision = "82a6b3c7d901"
down_revision = "3ec4765b3953"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("items") as batch:
        batch.drop_constraint("item_type", type_="check")
        batch.alter_column("item_type", existing_type=sa.String(10), type_=sa.String(16))
        batch.add_column(sa.Column("price_mode", sa.String(16), nullable=False, server_default="approximate"))
        batch.create_check_constraint("item_type", "item_type IN ('idea', 'gift', 'certificate')")
        batch.create_check_constraint("item_price_mode", "price_mode IN ('approximate', 'from')")
        batch.create_check_constraint(
            "certificate_url", "item_type <> 'certificate' OR url IS NOT NULL AND length(url) > 0"
        )


def downgrade():
    # Do not silently delete or turn certificate shops into unrelated wishes.
    connection = op.get_bind()
    if connection.scalar(sa.text("SELECT count(*) FROM items WHERE item_type = 'certificate'")):
        raise RuntimeError("Convert certificate entries before downgrading")
    with op.batch_alter_table("items") as batch:
        batch.drop_constraint("certificate_url", type_="check")
        batch.drop_constraint("item_price_mode", type_="check")
        batch.drop_constraint("item_type", type_="check")
        batch.drop_column("price_mode")
        batch.alter_column("item_type", existing_type=sa.String(16), type_=sa.String(10))
        batch.create_check_constraint("item_type", "item_type IN ('idea', 'gift')")
