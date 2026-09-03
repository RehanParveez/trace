from __future__ import annotations
import asyncio
from uuid import uuid4
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.modules.identity.enums import PermissionKey
from app.modules.identity.models import Organization, Permission, PlatformAdmin, Role, User, OrganizationMembership
from app.modules.subscriptions.service import SubscriptionService

DEFAULT_ORGANIZATION = {
  "name": "Trace Organization",
  "slug": "trace-org",
}

DEFAULT_USER = {
  "email": "admin@trace.local",
  "password": "admin12312!",
  "first_name": "Trace",
  "last_name": "Administrator",
}

async def seed_identity() -> None:
  async with AsyncSessionLocal() as session:
    organization_result = await session.execute(
      select(Organization).where(
        Organization.slug == DEFAULT_ORGANIZATION["slug"]
      )
    )
    organization = organization_result.scalar_one_or_none()

    if organization is None:
      organization = Organization(
        id=uuid4(),
        name=DEFAULT_ORGANIZATION["name"],
        slug=DEFAULT_ORGANIZATION["slug"],
        is_active=True,
      )

      session.add(organization)
      await session.flush()

    subscription_service = SubscriptionService(session)
    await subscription_service.create_initial_subscription(
      organization,
      plan_slug="free",
    )

    permission_definitions = {
      PermissionKey.IDENTITY_READ: (
        "View identity information."
      ),
      PermissionKey.IDENTITY_MANAGE: (
        "Manage identity information."
      ),
      PermissionKey.ORGANIZATION_READ: (
        "View organization information."
      ),
      PermissionKey.ORGANIZATION_MANAGE: (
        "Manage organization settings."
      ),
      PermissionKey.ORGANIZATION_MEMBERS_MANAGE: (
        "Manage organization members."
      ),
      PermissionKey.SUBSCRIPTION_READ: "Read access to subscription data.",
      PermissionKey.SUBSCRIPTION_MANAGE: "Manage subscription plan.",
      PermissionKey.SUBSCRIPTION_BILLING_MANAGE: "Manage subscription billing.",
      
      PermissionKey.PROJECT_READ: (
        "View projects, clients, members, and milestones."
      ),
      PermissionKey.PROJECT_CREATE: (
        "Create projects and clients."
      ),
      PermissionKey.PROJECT_UPDATE: (
        "Update projects, clients, members, and milestones."
      ),
      PermissionKey.PROJECT_DELETE: (
        "Delete projects, clients, members, and milestones."
      ),
      
      PermissionKey.DRAWING_READ: (
        "View drawings and parsed BOQ data."
      ),
      PermissionKey.DRAWING_CREATE: (
        "Create drawings."
      ),
      PermissionKey.DRAWING_DELETE: (
        "Delete drawings."
      ),
      PermissionKey.BOQ_UPDATE: (
        "Update BOQ data."
      ),
      PermissionKey.BOQ_APPROVE: (
        "Approve BOQ data."
      ),
      PermissionKey.MATERIAL_LIBRARY_MANAGE: (
        "Manage material library."
      ),
      PermissionKey.AUDIT_LOG_READ: (
        "View the organization's audit trail."
      ),
      
      PermissionKey.AI_REQUEST_READ: (
        "View the organization's AI request and response log.",
      ), 
      
     }

    permissions: dict[str, Permission] = {}
    for key, description in permission_definitions.items():
      result = await session.execute(
        select(Permission).where(
          Permission.key == key.value
        )
      )
      permission = result.scalar_one_or_none()
      if permission is None:
        permission = Permission(
          id=uuid4(),
          key=key.value,
          description=description,
        )
        session.add(permission)
        await session.flush()
      permissions[key.value] = permission

    role_result = await session.execute(
      select(Role).where(
        Role.organization_id == organization.id,
        Role.name == "Company Admin",
      )
    )

    role = role_result.scalar_one_or_none()
    if role is None:
      role = Role(
        id=uuid4(),
        organization_id=organization.id,
        name="Company Admin",
        description="Full administrative access to the organization.",
        is_system=True,
      )
      role.permissions = list(permissions.values())
      session.add(role)
      await session.flush()
    else:
      role.permissions = list(permissions.values())

    target_email = "npm@gmail.com"
    user = (
      await session.execute(
        select(User).where(User.email == target_email)
      )
    ).scalar_one_or_none()

    if user is not None:
      user_role = (
        await session.execute(
          select(Role).where(Role.id == user.role_id)
        )
      ).scalar_one_or_none()

      if user_role is not None:
        current_keys = {p.key for p in user_role.permissions}
        new_perms = [
          p for key, p in permissions.items()
          if key not in current_keys
        ]
        if new_perms:
          user_role.permissions.extend(new_perms)
          print(f"Granted new permissions to role '{user_role.name}' for user {target_email}")
        else:
          print(f"Role '{user_role.name}' for {target_email} already has all permissions")
      else:
        print(f"Role not found for user {target_email}")
    else:
      print(f"User {target_email} not found; skipping permission grant")

    user_result = await session.execute(
      select(User).where(
        User.email == DEFAULT_USER["email"]
      )
    )
    user = user_result.scalar_one_or_none()
    if user is None:
      user = User(
        id=uuid4(),
        organization_id=organization.id,
        role_id=role.id,
        email=DEFAULT_USER["email"],
        password_hash=hash_password(DEFAULT_USER["password"]),
        first_name=DEFAULT_USER["first_name"],
        last_name=DEFAULT_USER["last_name"],
        is_active=True,
        is_verified=True,
      )
      session.add(user)
      await session.flush()
    else:
      user.organization_id = organization.id
      user.role_id = role.id
      user.is_active = True
      user.is_verified = True
    
    membership_result = await session.execute(
      select(OrganizationMembership).where(
        OrganizationMembership.user_id == user.id,
        OrganizationMembership.organization_id == organization.id,
      )
    )
    membership = membership_result.scalar_one_or_none()

    if membership is None:
      session.add(
        OrganizationMembership(
          user_id=user.id,
          organization_id=organization.id,
          role_id=role.id,
          is_active=True,
        )
      )

    platform_admin_result = await session.execute(
      select(PlatformAdmin).where(
        PlatformAdmin.user_id == user.id
      )
    )
    platform_admin = platform_admin_result.scalar_one_or_none()

    if platform_admin is None:
      platform_admin = PlatformAdmin(
        user_id=user.id,
      )
      session.add(platform_admin)
    await session.commit()
    print("Identity seed completed.")
    print(f"Organization: {organization.slug}")
    print(f"Email: {DEFAULT_USER['email']}")
    print(f"Password: {DEFAULT_USER['password']}")

if __name__ == "__main__":
  asyncio.run(seed_identity())