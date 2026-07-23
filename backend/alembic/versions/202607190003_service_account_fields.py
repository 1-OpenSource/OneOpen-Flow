"""Service account client_id and description

Revision ID: 202607190003
Revises: 202607190002
Create Date: 2026-07-19
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "202607190003"
down_revision: Union[str, None] = "202607190002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("api_keys") as batch:
        batch.add_column(sa.Column("client_id", sa.String(length=120), nullable=True))
        batch.add_column(sa.Column("description", sa.Text(), nullable=True))

    # Backfill unique client_ids for existing rows
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id FROM api_keys")).fetchall()
    for row in rows:
        cid = f"svc-{str(row[0]).replace('-', '')[:16]}"
        conn.execute(
            sa.text("UPDATE api_keys SET client_id = :cid WHERE id = :id"),
            {"cid": cid, "id": str(row[0])},
        )

    with op.batch_alter_table("api_keys") as batch:
        batch.alter_column("client_id", existing_type=sa.String(length=120), nullable=False)
        batch.create_unique_constraint("uq_api_keys_client_id", ["client_id"])
        batch.create_index("ix_api_keys_client_id", ["client_id"])


def downgrade() -> None:
    with op.batch_alter_table("api_keys") as batch:
        batch.drop_index("ix_api_keys_client_id")
        batch.drop_constraint("uq_api_keys_client_id", type_="unique")
        batch.drop_column("description")
        batch.drop_column("client_id")
