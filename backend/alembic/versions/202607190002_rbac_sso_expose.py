"""RBAC, SSO, exposed workflows, API keys

Revision ID: 202607190002
Revises: 202607190001
Create Date: 2026-07-19
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "202607190002"
down_revision: Union[str, None] = "202607190001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.alter_column("password_hash", existing_type=sa.String(length=255), nullable=True)
        batch.add_column(sa.Column("auth_provider", sa.String(length=40), nullable=False, server_default="local"))
        batch.add_column(sa.Column("sso_subject", sa.String(length=255), nullable=True))
        batch.create_unique_constraint("uq_users_sso_subject", ["sso_subject"])

    with op.batch_alter_table("workflows") as batch:
        batch.add_column(sa.Column("is_exposed", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.add_column(sa.Column("expose_slug", sa.String(length=120), nullable=True))
        batch.add_column(sa.Column("expose_description", sa.Text(), nullable=True))
        batch.add_column(sa.Column("input_schema", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
        batch.create_unique_constraint("uq_workflows_expose_slug", ["expose_slug"])
        batch.create_index("ix_workflows_expose_slug", ["expose_slug"])

    op.create_table(
        "api_keys",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("prefix", sa.String(length=16), nullable=False),
        sa.Column("token_hash", sa.String(length=255), nullable=False),
        sa.Column("scopes", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_api_keys_prefix", "api_keys", ["prefix"])

    op.create_table(
        "user_invites",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=40), nullable=False),
        sa.Column("token_hash", sa.String(length=255), nullable=False),
        sa.Column("invited_by", sa.Uuid(), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["invited_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_user_invites_email", "user_invites", ["email"])

    op.create_table(
        "organization_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sso_enabled", sa.Boolean(), nullable=False),
        sa.Column("sso_provider_name", sa.String(length=80), nullable=False),
        sa.Column("oidc_issuer", sa.String(length=500), nullable=True),
        sa.Column("oidc_client_id", sa.String(length=255), nullable=True),
        sa.Column("oidc_client_secret_encrypted", sa.Text(), nullable=True),
        sa.Column("oidc_redirect_uri", sa.String(length=500), nullable=True),
        sa.Column("oidc_scopes", sa.String(length=255), nullable=False),
        sa.Column("oidc_default_role", sa.String(length=40), nullable=False),
        sa.Column("allow_local_login", sa.Boolean(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("organization_settings")
    op.drop_index("ix_user_invites_email", table_name="user_invites")
    op.drop_table("user_invites")
    op.drop_index("ix_api_keys_prefix", table_name="api_keys")
    op.drop_table("api_keys")
    with op.batch_alter_table("workflows") as batch:
        batch.drop_index("ix_workflows_expose_slug")
        batch.drop_constraint("uq_workflows_expose_slug", type_="unique")
        batch.drop_column("input_schema")
        batch.drop_column("expose_description")
        batch.drop_column("expose_slug")
        batch.drop_column("is_exposed")
    with op.batch_alter_table("users") as batch:
        batch.drop_constraint("uq_users_sso_subject", type_="unique")
        batch.drop_column("sso_subject")
        batch.drop_column("auth_provider")
        batch.alter_column("password_hash", existing_type=sa.String(length=255), nullable=False)
