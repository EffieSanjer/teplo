"""Remember imported site icons and logos without changing existing media."""

import sqlalchemy as sa
from alembic import op

revision = "97bc42d8a610"
down_revision = "82a6b3c7d901"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("media", sa.Column("is_icon", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade():
    op.drop_column("media", "is_icon")
