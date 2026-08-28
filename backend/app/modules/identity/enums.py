from enum import StrEnum

class TokenType(StrEnum):
  ACCESS = "access"
  REFRESH = "refresh"

class UserStatus(StrEnum):
  ACTIVE = "active"
  INACTIVE = "inactive"
  LOCKED = "locked"

class PermissionKey(StrEnum):
  IDENTITY_READ = "identity.read"
  IDENTITY_MANAGE = "identity.manage"
  ORGANIZATION_READ = "organization.read"
  ORGANIZATION_MANAGE = "organization.manage"
  ORGANIZATION_MEMBERS_MANAGE = "organization.members.manage"
  PROJECT_READ = "project.read"
  PROJECT_CREATE = "project.create"
  PROJECT_UPDATE = "project.update"
  PROJECT_DELETE = "project.delete"
  SUBSCRIPTION_READ = "subscription.read"
  SUBSCRIPTION_MANAGE = "subscription.manage"
  SUBSCRIPTION_BILLING_MANAGE = "subscription.billing.manage"