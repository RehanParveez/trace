from __future__ import annotations
import enum
import uuid
from datetime import datetime
from decimal import Decimal
from uuid import UUID
from sqlalchemy import BigInteger, Boolean, DateTime, Enum, ForeignKey, Index, JSON, Numeric, String, Text, UniqueConstraint, Integer
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.shared.mixins import TimestampMixin

class BillingInterval(str, enum.Enum):
  MONTHLY = "MONTHLY"
  YEARLY = "YEARLY"

class SubscriptionStatus(str, enum.Enum):
  TRIALING = "TRIALING"
  ACTIVE = "ACTIVE"
  PAST_DUE = "PAST_DUE"
  CANCELLED = "CANCELLED"
  EXPIRED = "EXPIRED"

class UsagePeriod(str, enum.Enum):
  MONTH = "MONTH"
  LIFETIME = "LIFETIME"

class Plan(Base, TimestampMixin):
  __tablename__ = "plans"

  id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    primary_key=True,
    default=uuid.uuid4,
  )

  name: Mapped[str] = mapped_column(
    String(100),
    nullable=False,
    unique=True,
  )

  slug: Mapped[str] = mapped_column(
    String(100),
    nullable=False,
    unique=True,
    index=True,
  )

  description: Mapped[str | None] = mapped_column(
    Text,
    nullable=True,
  )

  price_monthly: Mapped[Decimal] = mapped_column(
    Numeric(12, 2),
    nullable=False,
    default=Decimal("0"),
  )

  price_yearly: Mapped[Decimal] = mapped_column(
    Numeric(12, 2),
    nullable=False,
    default=Decimal("0"),
  )

  currency: Mapped[str] = mapped_column(
    String(3),
    nullable=False,
    default="PKR",
  )
  
  price_monthly_original: Mapped[Decimal | None] = mapped_column(
    Numeric(12, 2),
    nullable=True,
  )
  
  price_yearly_original: Mapped[Decimal | None] = mapped_column(
    Numeric(12, 2),
    nullable=True,
  )
  
  offer_label: Mapped[str | None] = mapped_column(
    String(120),
    nullable=True,
  )
  
  offer_ends_at: Mapped[datetime | None] = mapped_column(
    DateTime(timezone=True),
    nullable=True,
  )
  
  version: Mapped[int] = mapped_column(
    Integer,
    nullable=False,
    default=1
  )
  
  trial_days: Mapped[int] = mapped_column(
    Integer,
    nullable=False,
    default=0
  )
  
  sort_order: Mapped[int] = mapped_column(
    Integer,
    nullable=False,
    default=0
  )
  
  is_default: Mapped[bool] = mapped_column(
    Boolean,
    nullable=False,
    default=False
  )
    
  limit_policy: Mapped[dict] = mapped_column(
    JSON,
    nullable=False,
    default=dict,
  )

  is_active: Mapped[bool] = mapped_column(
    Boolean,
    nullable=False,
    default=True,
    index=True,
  )

  is_public: Mapped[bool] = mapped_column(
    Boolean,
    nullable=False,
    default=True,
  )

  features: Mapped[dict] = mapped_column(
    JSON,
    nullable=False,
    default=dict,
  )

  quotas: Mapped[dict] = mapped_column(
    JSON,
    nullable=False,
    default=dict,
  )

  subscriptions: Mapped[list["Subscription"]] = relationship(
    "Subscription",
    back_populates="plan",
  )

class Subscription(Base, TimestampMixin):
  __tablename__ = "subscriptions"

  __table_args__ = (
    UniqueConstraint(
      "organization_id",
      name="uq_subscriptions_organization",
    ),
    Index(
      "ix_subscriptions_org_status",
      "organization_id",
      "status",
    ),
  )

  id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    primary_key=True,
    default=uuid.uuid4,
  )

  organization_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey(
      "organizations.id",
      ondelete="CASCADE",
    ),
    nullable=False,
    index=True,
  )

  plan_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey(
      "plans.id",
      ondelete="RESTRICT",
    ),
    nullable=False,
    index=True,
  )

  status: Mapped[SubscriptionStatus] = mapped_column(
    Enum(
      SubscriptionStatus,
      name="subscription_status",
    ),
    nullable=False,
    default=SubscriptionStatus.ACTIVE,
    index=True,
  )

  billing_interval: Mapped[BillingInterval] = mapped_column(
    Enum(
      BillingInterval,
      name="billing_interval",
    ),
    nullable=False,
    default=BillingInterval.MONTHLY,
  )
  
  quantity: Mapped[int] = mapped_column(
    Integer,
    nullable=False,
    default=1,
  )

  grace_period_ends_at: Mapped[datetime | None] = mapped_column(
    DateTime(timezone=True),
    nullable=True,
  )
  
  cancellation_reason: Mapped[str | None] = mapped_column(
    String(255),
    nullable=True,
  )
  
  cancellation_feedback: Mapped[str | None] = mapped_column(
    Text,
    nullable=True,
  )

  last_payment_at: Mapped[datetime | None] = mapped_column(
    DateTime(timezone=True),
    nullable=True,
  )
  
  next_billing_at: Mapped[datetime | None] = mapped_column(
    DateTime(timezone=True),
    nullable=True,
  )

  started_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True),
    nullable=False,
  )

  current_period_start: Mapped[datetime] = mapped_column(
    DateTime(timezone=True),
    nullable=False,
  )

  current_period_end: Mapped[datetime] = mapped_column(
    DateTime(timezone=True),
    nullable=False,
  )

  trial_ends_at: Mapped[datetime | None] = mapped_column(
    DateTime(timezone=True),
    nullable=True,
  )

  cancelled_at: Mapped[datetime | None] = mapped_column(
    DateTime(timezone=True),
    nullable=True,
  )

  cancel_at_period_end: Mapped[bool] = mapped_column(
    Boolean,
    nullable=False,
    default=False,
  )

  provider: Mapped[str] = mapped_column(
    String(50),
    nullable=False,
    default="manual",
  )

  provider_customer_id: Mapped[str | None] = mapped_column(
    String(255),
    nullable=True,
  )

  provider_subscription_id: Mapped[str | None] = mapped_column(
    String(255),
    nullable=True,
  )

  plan: Mapped["Plan"] = relationship(
    "Plan",
    back_populates="subscriptions",
  )

  organization = relationship(
    "Organization",
    lazy="joined",
  )

class UsageCounter(Base, TimestampMixin):
  __tablename__ = "usage_counters"

  __table_args__ = (
    UniqueConstraint(
      "organization_id",
      "metric",
      "period_start",
      "period_end",
      name="uq_usage_counter_period",
    ),
    Index(
      "ix_usage_counters_org_metric",
      "organization_id",
      "metric",
    ),
  )

  id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    primary_key=True,
    default=uuid.uuid4,
  )

  organization_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey(
      "organizations.id",
      ondelete="CASCADE",
    ),
    nullable=False,
    index=True,
  )

  metric: Mapped[str] = mapped_column(
    String(100),
    nullable=False,
  )

  period: Mapped[UsagePeriod] = mapped_column(
    Enum(
      UsagePeriod,
      name="usage_period",
    ),
    nullable=False,
    default=UsagePeriod.MONTH,
  )

  period_start: Mapped[datetime] = mapped_column(
    DateTime(timezone=True),
    nullable=False,
  )

  period_end: Mapped[datetime] = mapped_column(
    DateTime(timezone=True),
    nullable=False,
  )

  quantity: Mapped[int] = mapped_column(
    BigInteger,
    nullable=False,
    default=0,
  )

  organization = relationship(
    "Organization",
    lazy="joined",
  )
  
class InvoiceStatus(str, enum.Enum):
  DRAFT = "DRAFT"
  OPEN = "OPEN"
  PAID = "PAID"
  VOID = "VOID"
  UNCOLLECTIBLE = "UNCOLLECTIBLE"

class PaymentStatus(str, enum.Enum):
  PENDING = "PENDING"
  SUCCEEDED = "SUCCEEDED"
  FAILED = "FAILED"
  REFUNDED = "REFUNDED"
  
class Invoice(Base, TimestampMixin):
  __tablename__ = "invoices"

  __table_args__ = (
    Index(
      "ix_invoices_org_status",
      "organization_id",
      "status",
    ),
  )

  id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    primary_key=True,
    default=uuid.uuid4,
  )

  organization_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey(
      "organizations.id",
      ondelete="CASCADE",
    ),
    nullable=False,
    index=True,
  )

  subscription_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey(
      "subscriptions.id",
      ondelete="SET NULL",
    ),
    nullable=True,
    index=True,
  )

  plan_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey(
      "plans.id",
      ondelete="SET NULL",
    ),
    nullable=True,
  )

  status: Mapped[InvoiceStatus] = mapped_column(
    Enum(
      InvoiceStatus,
      name="invoice_status",
    ),
    nullable=False,
    default=InvoiceStatus.DRAFT,
  )

  currency: Mapped[str] = mapped_column(
    String(3),
    nullable=False,
    default="PKR",
  )

  subtotal: Mapped[Decimal] = mapped_column(
    Numeric(12, 2),
    nullable=False,
    default=Decimal("0"),
  )

  tax: Mapped[Decimal] = mapped_column(
    Numeric(12, 2),
    nullable=False,
    default=Decimal("0"),
  )

  total: Mapped[Decimal] = mapped_column(
    Numeric(12, 2),
    nullable=False,
    default=Decimal("0"),
  )

  amount_paid: Mapped[Decimal] = mapped_column(
    Numeric(12, 2),
    nullable=False,
    default=Decimal("0"),
  )

  amount_due: Mapped[Decimal] = mapped_column(
    Numeric(12, 2),
    nullable=False,
    default=Decimal("0"),
  )

  period_start: Mapped[datetime] = mapped_column(
    DateTime(timezone=True),
    nullable=False,
  )

  period_end: Mapped[datetime] = mapped_column(
    DateTime(timezone=True),
    nullable=False,
  )

  due_date: Mapped[datetime | None] = mapped_column(
    DateTime(timezone=True),
    nullable=True,
  )

  paid_at: Mapped[datetime | None] = mapped_column(
    DateTime(timezone=True),
    nullable=True,
  )

  provider: Mapped[str] = mapped_column(
    String(50),
    nullable=False,
    default="manual",
  )

  provider_invoice_id: Mapped[str | None] = mapped_column(
    String(255),
    nullable=True,
  )

  line_items: Mapped[dict] = mapped_column(
    JSON,
    nullable=False,
    default=list,
  ) 

  metadata_: Mapped[dict] = mapped_column(
    "metadata",
    JSON,
    nullable=False,
    default=dict,
  )

  organization = relationship(
    "Organization",
    lazy="joined",
  )

  subscription = relationship(
    "Subscription",
    lazy="joined",
  )

  payments: Mapped[list["Payment"]] = relationship(
    "Payment",
    back_populates="invoice",
  )
  
  class Payment(Base, TimestampMixin):
    __tablename__ = "payments"

    __table_args__ = (
    Index(
      "ix_payments_org_status",
      "organization_id",
      "status",
    ),
  )

    id: Mapped[UUID] = mapped_column(
      PGUUID(as_uuid=True),
      primary_key=True,
      default=uuid.uuid4,
    )

    organization_id: Mapped[UUID] = mapped_column(
      PGUUID(as_uuid=True),
      ForeignKey(
       "organizations.id",
       ondelete="CASCADE",
      ),
      nullable=False,
      index=True,
    )

    invoice_id: Mapped[UUID | None] = mapped_column(
      PGUUID(as_uuid=True),
      ForeignKey(
       "invoices.id",
       ondelete="SET NULL",
      ),
      nullable=True,
      index=True,
    )

    subscription_id: Mapped[UUID | None] = mapped_column(
      PGUUID(as_uuid=True),
      ForeignKey(
       "subscriptions.id",
       ondelete="SET NULL",
      ),
      nullable=True,
    )

    status: Mapped[PaymentStatus] = mapped_column(
      Enum(
       PaymentStatus,
       name="payment_status",
      ),
      nullable=False,
      default=PaymentStatus.PENDING,
    )

    amount: Mapped[Decimal] = mapped_column(
      Numeric(12, 2),
      nullable=False,
    )

    currency: Mapped[str] = mapped_column(
      String(3),
      nullable=False,
      default="PKR",
    )

    provider: Mapped[str] = mapped_column(
      String(50),
      nullable=False,
      default="manual",
    ) 

    provider_payment_id: Mapped[str | None] = mapped_column(
      String(255),
      nullable=True,
    )

    paid_at: Mapped[datetime | None] = mapped_column(
      DateTime(timezone=True),
      nullable=True,
    )

    failure_reason: Mapped[str | None] = mapped_column(
      String(500),
      nullable=True,
    )

    metadata_: Mapped[dict] = mapped_column(
      "metadata",
      JSON,
      nullable=False,
      default=dict,
    )

    invoice: Mapped["Invoice | None"] = relationship(
      "Invoice",
      back_populates="payments",
    )