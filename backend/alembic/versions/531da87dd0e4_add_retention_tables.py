"""add retention tables

Revision ID: 531da87dd0e4
Revises: 7df245a018d7
Create Date: 2026-09-23 03:08:44.798927
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '531da87dd0e4'
down_revision: Union[str, Sequence[str], None] = '7df245a018d7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.alter_column('budget_categories', 'allocated_amount',
               existing_type=sa.NUMERIC(precision=18, scale=2),
               server_default=None,
               existing_nullable=False)
    op.drop_index(op.f('ix_budget_categories_organization'), table_name='budget_categories')
    op.create_index(op.f('ix_budget_categories_organization_id'), 'budget_categories', ['organization_id'], unique=False)
    op.alter_column('expenses', 'status',
               existing_type=postgresql.ENUM('PENDING', 'APPROVED', 'REJECTED', name='expense_status'),
               server_default=None,
               existing_nullable=False)
    op.alter_column('labour_deployments', 'status',
               existing_type=postgresql.ENUM('ACTIVE', 'ENDED', name='labour_deployment_status'),
               server_default=None,
               existing_nullable=False)
    op.alter_column('labour_payments', 'advance_recovered_amount',
               existing_type=sa.NUMERIC(precision=14, scale=2),
               server_default=None,
               existing_nullable=False)
    op.alter_column('labour_payments', 'wht_deducted_amount',
               existing_type=sa.NUMERIC(precision=14, scale=2),
               server_default=None,
               existing_nullable=False)
    op.alter_column('labour_sources', 'is_active_taxpayer',
               existing_type=sa.BOOLEAN(),
               server_default=None,
               existing_nullable=False)
    op.alter_column('labour_sources', 'is_active',
               existing_type=sa.BOOLEAN(),
               server_default=None,
               existing_nullable=False)
    op.alter_column('labour_workers', 'is_active',
               existing_type=sa.BOOLEAN(),
               server_default=None,
               existing_nullable=False)
    op.drop_index(op.f('ix_material_normalization_cache_organization'), table_name='material_normalization_cache')
    op.create_index(op.f('ix_material_normalization_cache_organization_id'), 'material_normalization_cache', ['organization_id'], unique=False)
    op.drop_index(op.f('ix_photo_tags_organization'), table_name='photo_tags')
    op.create_index(op.f('ix_photo_tags_organization_id'), 'photo_tags', ['organization_id'], unique=False)
    op.alter_column('plans', 'version',
               existing_type=sa.INTEGER(),
               server_default=None,
               existing_nullable=False)
    op.alter_column('plans', 'trial_days',
               existing_type=sa.INTEGER(),
               server_default=None,
               existing_nullable=False)
    op.alter_column('plans', 'sort_order',
               existing_type=sa.INTEGER(),
               server_default=None,
               existing_nullable=False)
    op.alter_column('plans', 'is_default',
               existing_type=sa.BOOLEAN(),
               server_default=None,
               existing_nullable=False)
    op.alter_column('plans', 'limit_policy',
               existing_type=postgresql.JSON(astext_type=sa.Text()),
               server_default=None,
               existing_nullable=False)
    op.alter_column('procurement_requests', 'status',
               existing_type=postgresql.ENUM('REQUESTED', 'APPROVED', 'ORDERED', 'RECEIVED', 'CANCELLED', name='procurement_status'),
               server_default=None,
               existing_nullable=False)
    op.alter_column('running_bill_line_items', 'sort_order',
               existing_type=sa.INTEGER(),
               server_default=None,
               existing_nullable=False)
    op.alter_column('running_bill_line_items', 'previous_percentage',
               existing_type=sa.NUMERIC(precision=5, scale=2),
               server_default=None,
               existing_nullable=False)
    op.alter_column('running_bill_line_items', 'cumulative_percentage',
               existing_type=sa.NUMERIC(precision=5, scale=2),
               server_default=None,
               existing_nullable=False)
    op.alter_column('running_bill_line_items', 'previous_quantity',
               existing_type=sa.NUMERIC(precision=18, scale=3),
               server_default=None,
               existing_nullable=False)
    op.alter_column('running_bill_line_items', 'cumulative_quantity',
               existing_type=sa.NUMERIC(precision=18, scale=3),
               server_default=None,
               existing_nullable=False)
    op.alter_column('running_bill_line_items', 'this_period_quantity',
               existing_type=sa.NUMERIC(precision=18, scale=3),
               server_default=None,
               existing_nullable=False)
    op.alter_column('running_bill_line_items', 'previous_value',
               existing_type=sa.NUMERIC(precision=18, scale=2),
               server_default=None,
               existing_nullable=False)
    op.alter_column('running_bill_line_items', 'cumulative_value',
               existing_type=sa.NUMERIC(precision=18, scale=2),
               server_default=None,
               existing_nullable=False)
    op.alter_column('running_bill_line_items', 'this_period_value',
               existing_type=sa.NUMERIC(precision=18, scale=2),
               server_default=None,
               existing_nullable=False)
    op.drop_index(op.f('ix_running_bill_line_items_bill'), table_name='running_bill_line_items')
    op.alter_column('running_bills', 'status',
               existing_type=postgresql.ENUM('DRAFT', 'ISSUED', 'CANCELLED', name='running_bill_status'),
               server_default=None,
               existing_nullable=False)
    op.alter_column('running_bills', 'gross_value_this_period',
               existing_type=sa.NUMERIC(precision=18, scale=2),
               server_default=None,
               existing_nullable=False)
    op.alter_column('running_bills', 'gross_value_cumulative',
               existing_type=sa.NUMERIC(precision=18, scale=2),
               server_default=None,
               existing_nullable=False)
    op.alter_column('running_bills', 'retention_percentage',
               existing_type=sa.NUMERIC(precision=5, scale=2),
               server_default=None,
               existing_nullable=False)
    op.alter_column('running_bills', 'retention_this_period',
               existing_type=sa.NUMERIC(precision=18, scale=2),
               server_default=None,
               existing_nullable=False)
    op.alter_column('running_bills', 'retention_cumulative',
               existing_type=sa.NUMERIC(precision=18, scale=2),
               server_default=None,
               existing_nullable=False)
    op.alter_column('running_bills', 'advance_recovery_amount',
               existing_type=sa.NUMERIC(precision=18, scale=2),
               server_default=None,
               existing_nullable=False)
    op.alter_column('running_bills', 'other_deductions_amount',
               existing_type=sa.NUMERIC(precision=18, scale=2),
               server_default=None,
               existing_nullable=False)
    op.alter_column('running_bills', 'net_payable',
               existing_type=sa.NUMERIC(precision=18, scale=2),
               server_default=None,
               existing_nullable=False)
    op.alter_column('running_bills', 'currency',
               existing_type=sa.VARCHAR(length=3),
               server_default=None,
               existing_nullable=False)
    op.create_index('ix_site_logs_project', 'site_logs', ['project_id'], unique=False)
    op.alter_column('subcontract_agreement_items', 'sort_order',
               existing_type=sa.INTEGER(),
               server_default=None,
               existing_nullable=False)
    op.drop_index(op.f('ix_subcontract_agreement_items_agreement'), table_name='subcontract_agreement_items')
    op.alter_column('subcontract_agreements', 'default_retention_percentage',
               existing_type=sa.NUMERIC(precision=5, scale=2),
               server_default=None,
               existing_nullable=False)
    op.alter_column('subcontract_agreements', 'status',
               existing_type=postgresql.ENUM('ACTIVE', 'COMPLETED', 'TERMINATED', name='subcontract_agreement_status'),
               server_default=None,
               existing_nullable=False)
    op.alter_column('subcontractor_bill_line_items', 'sort_order',
               existing_type=sa.INTEGER(),
               server_default=None,
               existing_nullable=False)
    op.alter_column('subcontractor_bill_line_items', 'previous_percentage',
               existing_type=sa.NUMERIC(precision=5, scale=2),
               server_default=None,
               existing_nullable=False)
    op.alter_column('subcontractor_bill_line_items', 'cumulative_percentage',
               existing_type=sa.NUMERIC(precision=5, scale=2),
               server_default=None,
               existing_nullable=False)
    op.alter_column('subcontractor_bill_line_items', 'this_period_value',
               existing_type=sa.NUMERIC(precision=16, scale=2),
               server_default=None,
               existing_nullable=False)
    op.alter_column('subcontractor_bill_line_items', 'cumulative_value',
               existing_type=sa.NUMERIC(precision=16, scale=2),
               server_default=None,
               existing_nullable=False)
    op.drop_index(op.f('ix_subcontractor_bill_line_items_bill'), table_name='subcontractor_bill_line_items')
    op.alter_column('subcontractor_bills', 'status',
               existing_type=postgresql.ENUM('DRAFT', 'ISSUED', 'CANCELLED', name='subcontractor_bill_status'),
               server_default=None,
               existing_nullable=False)
    op.alter_column('subcontractor_bills', 'gross_value_this_period',
               existing_type=sa.NUMERIC(precision=16, scale=2),
               server_default=None,
               existing_nullable=False)
    op.alter_column('subcontractor_bills', 'gross_value_cumulative',
               existing_type=sa.NUMERIC(precision=16, scale=2),
               server_default=None,
               existing_nullable=False)
    op.alter_column('subcontractor_bills', 'retention_percentage',
               existing_type=sa.NUMERIC(precision=5, scale=2),
               server_default=None,
               existing_nullable=False)
    op.alter_column('subcontractor_bills', 'retention_this_period',
               existing_type=sa.NUMERIC(precision=16, scale=2),
               server_default=None,
               existing_nullable=False)
    op.alter_column('subcontractor_bills', 'retention_cumulative',
               existing_type=sa.NUMERIC(precision=16, scale=2),
               server_default=None,
               existing_nullable=False)
    op.alter_column('subcontractor_bills', 'other_deductions_amount',
               existing_type=sa.NUMERIC(precision=16, scale=2),
               server_default=None,
               existing_nullable=False)
    op.alter_column('subcontractor_bills', 'net_payable',
               existing_type=sa.NUMERIC(precision=16, scale=2),
               server_default=None,
               existing_nullable=False)
    op.alter_column('subcontractor_bills', 'currency',
               existing_type=sa.VARCHAR(length=3),
               server_default=None,
               existing_nullable=False)
    op.alter_column('subcontractor_payments', 'advance_recovered_amount',
               existing_type=sa.NUMERIC(precision=16, scale=2),
               server_default=None,
               existing_nullable=False)
    op.alter_column('subcontractor_payments', 'wht_deducted_amount',
               existing_type=sa.NUMERIC(precision=16, scale=2),
               server_default=None,
               existing_nullable=False)
    op.alter_column('subcontractors', 'is_active_taxpayer',
               existing_type=sa.BOOLEAN(),
               server_default=None,
               existing_nullable=False)
    op.alter_column('subcontractors', 'is_active',
               existing_type=sa.BOOLEAN(),
               server_default=None,
               existing_nullable=False)
    op.alter_column('subscriptions', 'quantity',
               existing_type=sa.INTEGER(),
               server_default=None,
               existing_nullable=False)
    op.alter_column('withholding_tax_deductions', 'currency',
               existing_type=sa.VARCHAR(length=3),
               server_default=None,
               existing_nullable=False)
    op.alter_column('withholding_tax_rates', 'is_active',
               existing_type=sa.BOOLEAN(),
               server_default=None,
               existing_nullable=False)
    # ### end Alembic commands ###

def downgrade() -> None:
  # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('withholding_tax_rates', 'is_active',
               existing_type=sa.BOOLEAN(),
               server_default=sa.text('true'),
               existing_nullable=False)
    op.alter_column('withholding_tax_deductions', 'currency',
               existing_type=sa.VARCHAR(length=3),
               server_default=sa.text("'PKR'::character varying"),
               existing_nullable=False)
    op.alter_column('subscriptions', 'quantity',
               existing_type=sa.INTEGER(),
               server_default=sa.text('1'),
               existing_nullable=False)
    op.alter_column('subcontractors', 'is_active',
               existing_type=sa.BOOLEAN(),
               server_default=sa.text('true'),
               existing_nullable=False)
    op.alter_column('subcontractors', 'is_active_taxpayer',
               existing_type=sa.BOOLEAN(),
               server_default=sa.text('false'),
               existing_nullable=False)
    op.alter_column('subcontractor_payments', 'wht_deducted_amount',
               existing_type=sa.NUMERIC(precision=16, scale=2),
               server_default=sa.text("'0'::numeric"),
               existing_nullable=False)
    op.alter_column('subcontractor_payments', 'advance_recovered_amount',
               existing_type=sa.NUMERIC(precision=16, scale=2),
               server_default=sa.text("'0'::numeric"),
               existing_nullable=False)
    op.alter_column('subcontractor_bills', 'currency',
               existing_type=sa.VARCHAR(length=3),
               server_default=sa.text("'PKR'::character varying"),
               existing_nullable=False)
    op.alter_column('subcontractor_bills', 'net_payable',
               existing_type=sa.NUMERIC(precision=16, scale=2),
               server_default=sa.text("'0'::numeric"),
               existing_nullable=False)
    op.alter_column('subcontractor_bills', 'other_deductions_amount',
               existing_type=sa.NUMERIC(precision=16, scale=2),
               server_default=sa.text("'0'::numeric"),
               existing_nullable=False)
    op.alter_column('subcontractor_bills', 'retention_cumulative',
               existing_type=sa.NUMERIC(precision=16, scale=2),
               server_default=sa.text("'0'::numeric"),
               existing_nullable=False)
    op.alter_column('subcontractor_bills', 'retention_this_period',
               existing_type=sa.NUMERIC(precision=16, scale=2),
               server_default=sa.text("'0'::numeric"),
               existing_nullable=False)
    op.alter_column('subcontractor_bills', 'retention_percentage',
               existing_type=sa.NUMERIC(precision=5, scale=2),
               server_default=sa.text("'10'::numeric"),
               existing_nullable=False)
    op.alter_column('subcontractor_bills', 'gross_value_cumulative',
               existing_type=sa.NUMERIC(precision=16, scale=2),
               server_default=sa.text("'0'::numeric"),
               existing_nullable=False)
    op.alter_column('subcontractor_bills', 'gross_value_this_period',
               existing_type=sa.NUMERIC(precision=16, scale=2),
               server_default=sa.text("'0'::numeric"),
               existing_nullable=False)
    op.alter_column('subcontractor_bills', 'status',
               existing_type=postgresql.ENUM('DRAFT', 'ISSUED', 'CANCELLED', name='subcontractor_bill_status'),
               server_default=sa.text("'DRAFT'::subcontractor_bill_status"),
               existing_nullable=False)
    op.create_index(op.f('ix_subcontractor_bill_line_items_bill'), 'subcontractor_bill_line_items', ['bill_id'], unique=False)
    op.alter_column('subcontractor_bill_line_items', 'cumulative_value',
               existing_type=sa.NUMERIC(precision=16, scale=2),
               server_default=sa.text("'0'::numeric"),
               existing_nullable=False)
    op.alter_column('subcontractor_bill_line_items', 'this_period_value',
               existing_type=sa.NUMERIC(precision=16, scale=2),
               server_default=sa.text("'0'::numeric"),
               existing_nullable=False)
    op.alter_column('subcontractor_bill_line_items', 'cumulative_percentage',
               existing_type=sa.NUMERIC(precision=5, scale=2),
               server_default=sa.text("'0'::numeric"),
               existing_nullable=False)
    op.alter_column('subcontractor_bill_line_items', 'previous_percentage',
               existing_type=sa.NUMERIC(precision=5, scale=2),
               server_default=sa.text("'0'::numeric"),
               existing_nullable=False)
    op.alter_column('subcontractor_bill_line_items', 'sort_order',
               existing_type=sa.INTEGER(),
               server_default=sa.text('0'),
               existing_nullable=False)
    op.alter_column('subcontract_agreements', 'status',
               existing_type=postgresql.ENUM('ACTIVE', 'COMPLETED', 'TERMINATED', name='subcontract_agreement_status'),
               server_default=sa.text("'ACTIVE'::subcontract_agreement_status"),
               existing_nullable=False)
    op.alter_column('subcontract_agreements', 'default_retention_percentage',
               existing_type=sa.NUMERIC(precision=5, scale=2),
               server_default=sa.text("'10'::numeric"),
               existing_nullable=False)
    op.create_index(op.f('ix_subcontract_agreement_items_agreement'), 'subcontract_agreement_items', ['agreement_id'], unique=False)
    op.alter_column('subcontract_agreement_items', 'sort_order',
               existing_type=sa.INTEGER(),
               server_default=sa.text('0'),
               existing_nullable=False)
    op.drop_index('ix_site_logs_project', table_name='site_logs')
    op.alter_column('running_bills', 'currency',
               existing_type=sa.VARCHAR(length=3),
               server_default=sa.text("'PKR'::character varying"),
               existing_nullable=False)
    op.alter_column('running_bills', 'net_payable',
               existing_type=sa.NUMERIC(precision=18, scale=2),
               server_default=sa.text("'0'::numeric"),
               existing_nullable=False)
    op.alter_column('running_bills', 'other_deductions_amount',
               existing_type=sa.NUMERIC(precision=18, scale=2),
               server_default=sa.text("'0'::numeric"),
               existing_nullable=False)
    op.alter_column('running_bills', 'advance_recovery_amount',
               existing_type=sa.NUMERIC(precision=18, scale=2),
               server_default=sa.text("'0'::numeric"),
               existing_nullable=False)
    op.alter_column('running_bills', 'retention_cumulative',
               existing_type=sa.NUMERIC(precision=18, scale=2),
               server_default=sa.text("'0'::numeric"),
               existing_nullable=False)
    op.alter_column('running_bills', 'retention_this_period',
               existing_type=sa.NUMERIC(precision=18, scale=2),
               server_default=sa.text("'0'::numeric"),
               existing_nullable=False)
    op.alter_column('running_bills', 'retention_percentage',
               existing_type=sa.NUMERIC(precision=5, scale=2),
               server_default=sa.text("'10'::numeric"),
               existing_nullable=False)
    op.alter_column('running_bills', 'gross_value_cumulative',
               existing_type=sa.NUMERIC(precision=18, scale=2),
               server_default=sa.text("'0'::numeric"),
               existing_nullable=False)
    op.alter_column('running_bills', 'gross_value_this_period',
               existing_type=sa.NUMERIC(precision=18, scale=2),
               server_default=sa.text("'0'::numeric"),
               existing_nullable=False)
    op.alter_column('running_bills', 'status',
               existing_type=postgresql.ENUM('DRAFT', 'ISSUED', 'CANCELLED', name='running_bill_status'),
               server_default=sa.text("'DRAFT'::running_bill_status"),
               existing_nullable=False)
    op.create_index(op.f('ix_running_bill_line_items_bill'), 'running_bill_line_items', ['bill_id'], unique=False)
    op.alter_column('running_bill_line_items', 'this_period_value',
               existing_type=sa.NUMERIC(precision=18, scale=2),
               server_default=sa.text("'0'::numeric"),
               existing_nullable=False)
    op.alter_column('running_bill_line_items', 'cumulative_value',
               existing_type=sa.NUMERIC(precision=18, scale=2),
               server_default=sa.text("'0'::numeric"),
               existing_nullable=False)
    op.alter_column('running_bill_line_items', 'previous_value',
               existing_type=sa.NUMERIC(precision=18, scale=2),
               server_default=sa.text("'0'::numeric"),
               existing_nullable=False)
    op.alter_column('running_bill_line_items', 'this_period_quantity',
               existing_type=sa.NUMERIC(precision=18, scale=3),
               server_default=sa.text("'0'::numeric"),
               existing_nullable=False)
    op.alter_column('running_bill_line_items', 'cumulative_quantity',
               existing_type=sa.NUMERIC(precision=18, scale=3),
               server_default=sa.text("'0'::numeric"),
               existing_nullable=False)
    op.alter_column('running_bill_line_items', 'previous_quantity',
               existing_type=sa.NUMERIC(precision=18, scale=3),
               server_default=sa.text("'0'::numeric"),
               existing_nullable=False)
    op.alter_column('running_bill_line_items', 'cumulative_percentage',
               existing_type=sa.NUMERIC(precision=5, scale=2),
               server_default=sa.text("'0'::numeric"),
               existing_nullable=False)
    op.alter_column('running_bill_line_items', 'previous_percentage',
               existing_type=sa.NUMERIC(precision=5, scale=2),
               server_default=sa.text("'0'::numeric"),
               existing_nullable=False)
    op.alter_column('running_bill_line_items', 'sort_order',
               existing_type=sa.INTEGER(),
               server_default=sa.text('0'),
               existing_nullable=False)
    op.alter_column('procurement_requests', 'status',
               existing_type=postgresql.ENUM('REQUESTED', 'APPROVED', 'ORDERED', 'RECEIVED', 'CANCELLED', name='procurement_status'),
               server_default=sa.text("'REQUESTED'::procurement_status"),
               existing_nullable=False)
    op.alter_column('plans', 'limit_policy',
               existing_type=postgresql.JSON(astext_type=sa.Text()),
               server_default=sa.text("'{}'::json"),
               existing_nullable=False)
    op.alter_column('plans', 'is_default',
               existing_type=sa.BOOLEAN(),
               server_default=sa.text('false'),
               existing_nullable=False)
    op.alter_column('plans', 'sort_order',
               existing_type=sa.INTEGER(),
               server_default=sa.text('0'),
               existing_nullable=False)
    op.alter_column('plans', 'trial_days',
               existing_type=sa.INTEGER(),
               server_default=sa.text('0'),
               existing_nullable=False)
    op.alter_column('plans', 'version',
               existing_type=sa.INTEGER(),
               server_default=sa.text('1'),
               existing_nullable=False)
    op.drop_index(op.f('ix_photo_tags_organization_id'), table_name='photo_tags')
    op.create_index(op.f('ix_photo_tags_organization'), 'photo_tags', ['organization_id'], unique=False)
    op.drop_index(op.f('ix_material_normalization_cache_organization_id'), table_name='material_normalization_cache')
    op.create_index(op.f('ix_material_normalization_cache_organization'), 'material_normalization_cache', ['organization_id'], unique=False)
    op.alter_column('labour_workers', 'is_active',
               existing_type=sa.BOOLEAN(),
               server_default=sa.text('true'),
               existing_nullable=False)
    op.alter_column('labour_sources', 'is_active',
               existing_type=sa.BOOLEAN(),
               server_default=sa.text('true'),
               existing_nullable=False)
    op.alter_column('labour_sources', 'is_active_taxpayer',
               existing_type=sa.BOOLEAN(),
               server_default=sa.text('false'),
               existing_nullable=False)
    op.alter_column('labour_payments', 'wht_deducted_amount',
               existing_type=sa.NUMERIC(precision=14, scale=2),
               server_default=sa.text("'0'::numeric"),
               existing_nullable=False)
    op.alter_column('labour_payments', 'advance_recovered_amount',
               existing_type=sa.NUMERIC(precision=14, scale=2),
               server_default=sa.text("'0'::numeric"),
               existing_nullable=False)
    op.alter_column('labour_deployments', 'status',
               existing_type=postgresql.ENUM('ACTIVE', 'ENDED', name='labour_deployment_status'),
               server_default=sa.text("'ACTIVE'::labour_deployment_status"),
               existing_nullable=False)
    op.alter_column('expenses', 'status',
               existing_type=postgresql.ENUM('PENDING', 'APPROVED', 'REJECTED', name='expense_status'),
               server_default=sa.text("'PENDING'::expense_status"),
               existing_nullable=False)
    op.drop_index(op.f('ix_budget_categories_organization_id'), table_name='budget_categories')
    op.create_index(op.f('ix_budget_categories_organization'), 'budget_categories', ['organization_id'], unique=False)
    op.alter_column('budget_categories', 'allocated_amount',
               existing_type=sa.NUMERIC(precision=18, scale=2),
               server_default=sa.text("'0'::numeric"),
               existing_nullable=False)