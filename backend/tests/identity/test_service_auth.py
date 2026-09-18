from __future__ import annotations
from datetime import datetime, timedelta, timezone
from uuid import uuid4
import pytest
from sqlalchemy import select
from app.core.exceptions import TraceException
from app.core.security import hash_password, verify_password
from app.modules.identity.models import Organization, OrganizationMembership, RefreshToken, Role, User
from app.modules.identity.service import MAX_FAILED_LOGIN_ATTEMPTS, IdentityService

async def _seed_org_role_user(
  db_session,
  *,
  email: str = "aayan@gmail.com",
  password: str = "Aayan12312#!",
  is_verified: bool = True,
  is_active: bool = True,
  org_active: bool = True,
  failed_attempts: int = 0,
  locked_until=None,
):
  org = Organization(
    id=uuid4(),
    name="Acme Construction",
    slug=f"acme-{uuid4().hex[:6]}",
    is_active=org_active,
  )
  role = Role(
    id=uuid4(),
    organization_id=org.id,
    name="Company Admin",
    is_system=True,
  )
  user = User(
    id=uuid4(),
    organization_id=org.id,
    role_id=role.id,
    email=email,
    password_hash=hash_password(password),
    first_name="Aayan",
    last_name="Builder",
    is_active=is_active,
    is_verified=is_verified,
    failed_login_attempts=failed_attempts,
    locked_until=locked_until,
  )
  membership = OrganizationMembership(
    id=uuid4(),
    user_id=user.id,
    organization_id=org.id,
    role_id=role.id,
    is_active=True,
  )
  db_session.add_all([org, role, user, membership])
  await db_session.flush()
  return org, role, user, membership


class AsyncMockSend:
  async def __call__(self, **kwargs):
    return None

@pytest.mark.integration
@pytest.mark.auth
@pytest.mark.asyncio
class TestAuthenticate:
  async def test_successful_authenticate(self, identity_service, db_session):
    _, _, user, _ = await _seed_org_role_user(db_session)
    result = await identity_service.authenticate(
      email=user.email, password="Aayan12312#!"
    )
    assert result.id == user.id

  async def test_unknown_email_raises_invalid_credentials(
    self, identity_service, db_session
  ):
    with pytest.raises(TraceException) as exc:
      await identity_service.authenticate(
        email="shabbir@gmail.com", password="Shabbir12312#!1"
      )
    assert exc.value.status_code == 401
    assert exc.value.code == "INVALID_CREDENTIALS"

  async def test_wrong_password_increments_failed_attempts(
    self, identity_service, db_session
  ):
    _, _, user, _ = await _seed_org_role_user(db_session)
    with pytest.raises(TraceException) as exc:
      await identity_service.authenticate(
        email=user.email, password="WrongPassword1!"
      )
    assert exc.value.code == "INVALID_CREDENTIALS"
    await db_session.refresh(user)
    assert user.failed_login_attempts == 1
    assert user.locked_until is None

  async def test_lockout_after_max_failed_attempts(
    self, identity_service, db_session
  ):
    _, _, user, _ = await _seed_org_role_user(
      db_session, failed_attempts=MAX_FAILED_LOGIN_ATTEMPTS - 1
    )
    with pytest.raises(TraceException):
      await identity_service.authenticate(
        email=user.email, password="WrongPassword1!"
      )
    await db_session.refresh(user)
    assert user.failed_login_attempts == MAX_FAILED_LOGIN_ATTEMPTS
    assert user.locked_until is not None
    assert user.locked_until > datetime.now(timezone.utc)

  async def test_locked_account_rejects_even_with_correct_password(
    self, identity_service, db_session
  ):
    locked_until = datetime.now(timezone.utc) + timedelta(minutes=10)
    _, _, user, _ = await _seed_org_role_user(db_session, locked_until=locked_until)
    with pytest.raises(TraceException) as exc:
      await identity_service.authenticate(
        email=user.email, password="Aayan12312#!"
      )
    assert exc.value.status_code == 429
    assert exc.value.code == "ACCOUNT_TEMPORARILY_LOCKED"

  async def test_inactive_user_rejected(self, identity_service, db_session):
    _, _, user, _ = await _seed_org_role_user(db_session, is_active=False)
    with pytest.raises(TraceException) as exc:
      await identity_service.authenticate(
        email=user.email, password="Aayan12312#!"
      )
    assert exc.value.code == "USER_INACTIVE"

  async def test_unverified_user_rejected(self, identity_service, db_session):
    _, _, user, _ = await _seed_org_role_user(db_session, is_verified=False)
    with pytest.raises(TraceException) as exc:
      await identity_service.authenticate(
        email=user.email, password="Aayan12312#!"
      )
    assert exc.value.code == "EMAIL_NOT_VERIFIED"

  async def test_inactive_organization_rejected(self, identity_service, db_session):
    _, _, user, _ = await _seed_org_role_user(db_session, org_active=False)
    with pytest.raises(TraceException) as exc:
      await identity_service.authenticate(
        email=user.email, password="Aayan12312#!"
      )
    assert exc.value.code == "ORGANIZATION_INACTIVE"

@pytest.mark.integration
@pytest.mark.auth
@pytest.mark.asyncio
class TestLogin:
  async def test_login_clears_failed_attempts(self, identity_service, db_session):
    _, _, user, _ = await _seed_org_role_user(db_session, failed_attempts=3)
    await identity_service.login(email=user.email, password="Aayan12312#!")
    await db_session.refresh(user)
    assert user.failed_login_attempts == 0
    assert user.locked_until is None
    assert user.last_login_at is not None

  async def test_resolve_login_membership_falls_back_to_another_active_org(
    self, identity_service, db_session
  ):
    org_a, role_a, user, mem_a = await _seed_org_role_user(db_session)
    mem_a.is_active = False
    await db_session.flush()

    org_b = Organization(
      id=uuid4(),
      name="Secondary Org",
      slug=f"sec-{uuid4().hex[:6]}",
      is_active=True,
    )
    role_b = Role(
      id=uuid4(), organization_id=org_b.id, name="Member", is_system=False
    )
    mem_b = OrganizationMembership(
      id=uuid4(),
      user_id=user.id,
      organization_id=org_b.id,
      role_id=role_b.id,
      is_active=True,
    )
    db_session.add_all([org_b, role_b, mem_b])
    await db_session.flush()

    membership = await identity_service.resolve_login_membership(user)
    assert membership.organization_id == org_b.id

  async def test_resolve_login_membership_raises_when_none_active(
    self, identity_service, db_session
  ):
    org, role, user, mem = await _seed_org_role_user(db_session)
    mem.is_active = False
    await db_session.flush()

    with pytest.raises(TraceException) as exc:
      await identity_service.resolve_login_membership(user)
    assert exc.value.code == "NO_ACTIVE_ORGANIZATION"

@pytest.mark.integration
@pytest.mark.auth
@pytest.mark.asyncio
class TestRegister:
  async def test_register_creates_org_role_user_membership(
    self, identity_service, db_session, monkeypatch
  ):
    class StubSubscriptionService:
      def __init__(self, session):
        pass

      async def create_initial_subscription(self, organization, plan_slug="free"):
        return None

    monkeypatch.setattr(
      "app.modules.identity.service.SubscriptionService",
      StubSubscriptionService,
    )
    identity_service.email_service.send = AsyncMockSend()

    response = await identity_service.register(
      email="new@example.com",
      password="BrandNewPass1!",
      password_confirmation="BrandNewPass1!",
      first_name="New",
      last_name="User",
      organization_name="Brand New Builders",
    )
    assert response.verification_required is True
    assert response.user.email == "new@example.com"
    assert response.user.is_verified is False

    result = await db_session.execute(
      select(User).where(User.email == "new@example.com")
    )
    user = result.scalar_one()
    assert user.is_verified is False
    assert verify_password("BrandNewPass1!", user.password_hash)

    result = await db_session.execute(
      select(OrganizationMembership).where(
        OrganizationMembership.user_id == user.id
      )
    )
    assert result.scalar_one() is not None

    result = await db_session.execute(
      select(Role).where(
        Role.organization_id == user.organization_id,
        Role.name == "Company Admin",
      )
    )
    assert result.scalar_one() is not None

  async def test_register_rejects_duplicate_email(
    self, identity_service, db_session, monkeypatch
  ):
    await _seed_org_role_user(db_session, email="taken@example.com")
    identity_service.email_service.send = AsyncMockSend()

    with pytest.raises(TraceException) as exc:
      await identity_service.register(
        email="taken@example.com",
        password="BrandNewPass1!",
        password_confirmation="BrandNewPass1!",
        first_name="X",
        last_name="Y",
        organization_name="Another Org",
      )
    assert exc.value.code == "EMAIL_ALREADY_REGISTERED"
    assert exc.value.status_code == 409

  async def test_register_rejects_duplicate_organization_name(
    self, identity_service, db_session, monkeypatch
  ):
    await _seed_org_role_user(db_session)
    identity_service.email_service.send = AsyncMockSend()

    with pytest.raises(TraceException) as exc:
      await identity_service.register(
        email="fresh@example.com",
        password="BrandNewPass1!",
        password_confirmation="BrandNewPass1!",
        first_name="X",
        last_name="Y",
        organization_name="Acme Construction",
      )
    assert exc.value.code == "ORGANIZATION_ALREADY_EXISTS"

@pytest.mark.integration
@pytest.mark.auth
@pytest.mark.asyncio
class TestRefreshAndLogout:
  async def test_refresh_rotates_tokens(self, identity_service, db_session):
    _, _, user, membership = await _seed_org_role_user(db_session)
    login = await identity_service.login(
      email=user.email, password="Aayan12312#!"
    )
    old_refresh = login.tokens.refresh_token

    new_tokens = await identity_service.refresh(raw_refresh_token=old_refresh)
    assert new_tokens.access_token
    assert new_tokens.refresh_token
    assert new_tokens.refresh_token != old_refresh

    token_hash = IdentityService.hash_refresh_token(old_refresh)
    result = await db_session.execute(
      select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    old_row = result.scalar_one()
    assert old_row.revoked_at is not None
    assert old_row.replaced_by_token_id is not None

  async def test_logout_revokes_single_token(self, identity_service, db_session):
    _, _, user, _ = await _seed_org_role_user(db_session)
    login = await identity_service.login(
      email=user.email, password="Aayan12312#!"
    )
    await identity_service.logout(raw_refresh_token=login.tokens.refresh_token)

    token_hash = IdentityService.hash_refresh_token(login.tokens.refresh_token)
    result = await db_session.execute(
      select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    row = result.scalar_one()
    assert row.revoked_at is not None

  async def test_logout_all_revokes_every_active_token(
    self, identity_service, db_session
  ):
    org, _, user, _ = await _seed_org_role_user(db_session)
    await identity_service.login(email=user.email, password="Aayan12312#!")

    db_session.add(
     RefreshToken(
      id=uuid4(),
      user_id=user.id,
      organization_id=org.id,
      token_hash=f"other-hash-{uuid4().hex}",
      expires_at=datetime.now(timezone.utc) + timedelta(days=7),
     )
    )
    await db_session.flush()
    await identity_service.logout_all(user.id)

    result = await db_session.execute(
     select(RefreshToken).where(
      RefreshToken.user_id == user.id,
      RefreshToken.revoked_at.is_(None),
     )
    )
    assert result.scalars().all() == []

@pytest.mark.integration
@pytest.mark.auth
@pytest.mark.asyncio
class TestSwitchOrganization:
  async def test_switch_to_active_membership(self, identity_service, db_session):
    org_a, role_a, user, mem_a = await _seed_org_role_user(db_session)

    org_b = Organization(
      id=uuid4(),
      name="Second Org",
      slug=f"second-{uuid4().hex[:6]}",
      is_active=True,
    )
    role_b = Role(
      id=uuid4(), organization_id=org_b.id, name="Viewer", is_system=False
    )
    mem_b = OrganizationMembership(
      id=uuid4(),
      user_id=user.id,
      organization_id=org_b.id,
      role_id=role_b.id,
      is_active=True,
    )
    db_session.add_all([org_b, role_b, mem_b])
    await db_session.flush()

    response = await identity_service.switch_organization(user, org_b.id)
    assert response.user.organization_id == org_b.id
    assert response.tokens.access_token

  async def test_switch_rejects_missing_membership(
    self, identity_service, db_session
  ):
    _, _, user, _ = await _seed_org_role_user(db_session)
    with pytest.raises(TraceException) as exc:
      await identity_service.switch_organization(user, uuid4())
    assert exc.value.code == "NO_ACTIVE_MEMBERSHIP"

@pytest.mark.integration
@pytest.mark.auth
@pytest.mark.asyncio
class TestPasswordAndVerificationFlows:
  async def test_change_password_success_and_revokes_sessions(
    self, identity_service, db_session
  ):
    _, _, user, _ = await _seed_org_role_user(db_session)
    await identity_service.login(email=user.email, password="Aayan12312#!")

    await identity_service.change_password(
      user=user,
      current_password="Aayan12312#!",
      new_password="EvenStronger99!",
      password_confirmation="EvenStronger99!",
    )
    await db_session.refresh(user)
    assert verify_password("EvenStronger99!", user.password_hash)

    result = await db_session.execute(
      select(RefreshToken).where(
        RefreshToken.user_id == user.id,
        RefreshToken.revoked_at.is_(None),
      )
    )
    assert result.scalars().all() == []

  async def test_change_password_rejects_wrong_current(
    self, identity_service, db_session
  ):
    _, _, user, _ = await _seed_org_role_user(db_session)
    with pytest.raises(TraceException) as exc:
      await identity_service.change_password(
        user=user,
        current_password="WrongCurrent1!",
        new_password="EvenStronger99!",
        password_confirmation="EvenStronger99!",
      )
    assert exc.value.code == "INVALID_CURRENT_PASSWORD"

  async def test_forgot_and_reset_password_flow(self, identity_service, db_session):
    _, _, user, _ = await _seed_org_role_user(db_session)
    identity_service.email_service.send = AsyncMockSend()

    token = await identity_service.forgot_password(email=user.email)
    assert token is not None

    await identity_service.reset_password(token=token, new_password="ResetPass99!")
    await db_session.refresh(user)
    assert verify_password("ResetPass99!", user.password_hash)

  async def test_email_verification_flow(self, identity_service, db_session):
    _, _, user, _ = await _seed_org_role_user(db_session, is_verified=False)
    token = await identity_service.create_email_verification_token(user)
    await identity_service.verify_email(token=token)
    await db_session.refresh(user)
    assert user.is_verified is True

    with pytest.raises(TraceException) as exc:
      await identity_service.verify_email(token=token)
    assert exc.value.code == "INVALID_VERIFICATION_TOKEN"