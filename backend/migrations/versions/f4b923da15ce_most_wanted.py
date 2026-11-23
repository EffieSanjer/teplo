"""Mark the owner's most wanted wishes."""

import sqlalchemy as sa
from alembic import op

revision = "f4b923da15ce"
down_revision = "e3a812c904bd"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("items", sa.Column("most_wanted", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade():
    op.drop_column("items", "most_wanted")
