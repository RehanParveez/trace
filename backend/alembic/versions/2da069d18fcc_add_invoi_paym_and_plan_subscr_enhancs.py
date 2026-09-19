"""add_invoi_paym_and_plan_subscr_enhancs

Revision ID: 2da069d18fcc
Revises: d1c2738da136
Create Date: 2026-09-19 17:33:05.053818
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "2da069d18fcc"
down_revision: Union[str, Sequence[str], None] = "d1c2738da136"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "invoices",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("subscription_id", sa.UUID(), nullable=True),
        sa.Column("plan_id", sa.UUID(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "DRAFT", "OPEN", "PAID", "VOID", "UNCOLLECTIBLE",
                name="invoice_status",
            ),
            nullable=False,
        ),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("subtotal", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("tax", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("total", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("amount_paid", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("amount_due", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("provider_invoice_id", sa.String(length=255), nullable=True),
        sa.Column("line_items", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["plan_id"], ["plans.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["subscription_id"], ["subscriptions.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_invoices_org_status",
        "invoices",
        ["organization_id", "status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_invoices_organization_id"),
        "invoices",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_invoices_subscription_id"),
        "invoices",
        ["subscription_id"],
        unique=False,
    )

    op.create_table(
        "payments",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("invoice_id", sa.UUID(), nullable=True),
        sa.Column("subscription_id", sa.UUID(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING", "SUCCEEDED", "FAILED", "REFUNDED",
                name="payment_status",
            ),
            nullable=False,
        ),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("provider_payment_id", sa.String(length=255), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_reason", sa.String(length=500), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["invoice_id"], ["invoices.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["subscription_id"], ["subscriptions.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_payments_invoice_id"),
        "payments",
        ["invoice_id"],
        unique=False,
    )
    op.create_index(
        "ix_payments_org_status",
        "payments",
        ["organization_id", "status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_payments_organization_id"),
        "payments",
        ["organization_id"],
        unique=False,
    )

    op.add_column(
        "plans",
        sa.Column("price_monthly_original", sa.Numeric(precision=12, scale=2), nullable=True),
    )
    op.add_column(
        "plans",
        sa.Column("price_yearly_original", sa.Numeric(precision=12, scale=2), nullable=True),
    )
    op.add_column(
        "plans",
        sa.Column("offer_label", sa.String(length=120), nullable=True),
    )
    op.add_column(
        "plans",
        sa.Column("offer_ends_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "plans",
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "plans",
        sa.Column("trial_days", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "plans",
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "plans",
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "plans",
        sa.Column("limit_policy", sa.JSON(), nullable=False, server_default="{}"),
    )

    op.add_column(
        "subscriptions",
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "subscriptions",
        sa.Column("grace_period_ends_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "subscriptions",
        sa.Column("cancellation_reason", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "subscriptions",
        sa.Column("cancellation_feedback", sa.Text(), nullable=True),
    )
    op.add_column(
        "subscriptions",
        sa.Column("last_payment_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "subscriptions",
        sa.Column("next_billing_at", sa.DateTime(timezone=True), nullable=True),
    )

def downgrade() -> None:
    op.drop_column("subscriptions", "next_billing_at")
    op.drop_column("subscriptions", "last_payment_at")
    op.drop_column("subscriptions", "cancellation_feedback")
    op.drop_column("subscriptions", "cancellation_reason")
    op.drop_column("subscriptions", "grace_period_ends_at")
    op.drop_column("subscriptions", "quantity")

    op.drop_column("plans", "limit_policy")
    op.drop_column("plans", "is_default")
    op.drop_column("plans", "sort_order")
    op.drop_column("plans", "trial_days")
    op.drop_column("plans", "version")
    op.drop_column("plans", "offer_ends_at")
    op.drop_column("plans", "offer_label")
    op.drop_column("plans", "price_yearly_original")
    op.drop_column("plans", "price_monthly_original")

    op.drop_index(op.f("ix_payments_organization_id"), table_name="payments")
    op.drop_index("ix_payments_org_status", table_name="payments")
    op.drop_index(op.f("ix_payments_invoice_id"), table_name="payments")
    op.drop_table("payments")

    op.drop_index(op.f("ix_invoices_subscription_id"), table_name="invoices")
    op.drop_index(op.f("ix_invoices_organization_id"), table_name="invoices")
    op.drop_index("ix_invoices_org_status", table_name="invoices")
    op.drop_table("invoices")