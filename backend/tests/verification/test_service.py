from __future__ import annotations
from uuid import uuid4, UUID
from decimal import Decimal
from app.modules.verification.schemas import ProgressClaimCreateRequest, ProgressClaimUpdateRequest, ProgressClaimReviewRequest, PhotoBOQLinkCreateRequest
from app.modules.verification.service import VerificationService
import pytest
from app.core.exceptions import TraceException
from app.modules.drawings_boq.models import BOQItemStatus
from app.modules.verification.models import ProgressClaimStatus, PhotoBOQLink
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

def _create_payload(
  project_id: UUID,
  boq_item_id: UUID,
  *,
  qty: Decimal = Decimal("12.5000"),
  pct: Decimal = Decimal("12.5000"),
) -> ProgressClaimCreateRequest:
  return ProgressClaimCreateRequest(
    project_id=project_id,
    boq_item_id=boq_item_id,
    claim_date=date.today(),
    claimed_quantity=qty,
    claimed_percentage=pct,
    notes="Foundation pour stage 1",
  )

@pytest.mark.asyncio
async def test_create_claim_success(
  verification_service: VerificationService,
  verification_admin_context,
  project_factory,
  make_boq_item,
  db_session,
):
  ctx = verification_admin_context
  project = await project_factory(organization=ctx.organization)
  boq = await make_boq_item(
    organization_id=ctx.organization.id,
    project_id=project.id,
    status=BOQItemStatus.APPROVED,
  )

  payload = _create_payload(project.id, boq.id)
  claim = await verification_service.create_claim(
    ctx.organization.id, ctx.user.id, payload
  )

  assert claim.id is not None
  assert claim.status == ProgressClaimStatus.DRAFT
  assert claim.version == 1
  assert claim.claimed_quantity == Decimal("12.5000")
  assert claim.organization_id == ctx.organization.id
  assert claim.submitted_by is None
  assert claim.reviewed_by is None

@pytest.mark.asyncio
async def test_create_claim_project_not_found(
  verification_service: VerificationService,
  verification_admin_context,
  make_boq_item,
):
  ctx = verification_admin_context
  fake_project_id = uuid4()
  with pytest.raises(TraceException) as exc:
    await verification_service.create_claim(
      ctx.organization.id,
      ctx.user.id,
      _create_payload(fake_project_id, uuid4()),
    )
  assert exc.value.status_code == 404
  assert exc.value.code == "PROJECT_NOT_FOUND"

@pytest.mark.asyncio
async def test_create_claim_boq_not_approved(
  verification_service: VerificationService,
  verification_admin_context,
  project_factory,
  make_boq_item,
):
  ctx = verification_admin_context
  project = await project_factory(organization=ctx.organization)
  boq = await make_boq_item(
    organization_id=ctx.organization.id,
    project_id=project.id,
    status=BOQItemStatus.DRAFT,
  )

  with pytest.raises(TraceException) as exc:
    await verification_service.create_claim(
      ctx.organization.id,
      ctx.user.id,
      _create_payload(project.id, boq.id),
    )
  assert exc.value.status_code == 404
  assert exc.value.code == "BOQ_ITEM_NOT_FOUND"

@pytest.mark.asyncio
async def test_update_draft_claim_success(
  verification_service: VerificationService,
  verification_admin_context,
  project_factory,
  make_boq_item,
  make_progress_claim,
):
  ctx = verification_admin_context
  project = await project_factory(organization=ctx.organization)
  boq = await make_boq_item(
    organization_id=ctx.organization.id, project_id=project.id
  )
  claim = await make_progress_claim(
    organization_id=ctx.organization.id,
    project_id=project.id,
    boq_item_id=boq.id,
    status=ProgressClaimStatus.DRAFT,
    version=1,
  )

  updated = await verification_service.update_claim(
    ctx.organization.id,
    claim.id,
    ProgressClaimUpdateRequest(
      claimed_quantity=Decimal("20.0000"),
      claimed_percentage=Decimal("20.0000"),
      version=1,
    ),
  )

  assert updated.claimed_quantity == Decimal("20.0000")
  assert updated.version == 2
  assert updated.status == ProgressClaimStatus.DRAFT

@pytest.mark.asyncio
async def test_update_non_draft_rejected(
  verification_service: VerificationService,
  verification_admin_context,
  project_factory,
  make_boq_item,
  make_progress_claim,
):
  ctx = verification_admin_context
  project = await project_factory(organization=ctx.organization)
  boq = await make_boq_item(
    organization_id=ctx.organization.id, project_id=project.id
  )
  claim = await make_progress_claim(
    organization_id=ctx.organization.id,
    project_id=project.id,
    boq_item_id=boq.id,
    status=ProgressClaimStatus.SUBMITTED,
    version=1,
  )

  with pytest.raises(TraceException) as exc:
    await verification_service.update_claim(
      ctx.organization.id,
      claim.id,
      ProgressClaimUpdateRequest(version=1, claimed_quantity=Decimal("5")),
    )
  assert exc.value.status_code == 409
  assert exc.value.code == "PROGRESS_CLAIM_NOT_DRAFT"

@pytest.mark.asyncio
async def test_update_concurrent_modification(
  verification_service: VerificationService,
  verification_admin_context,
  project_factory,
  make_boq_item,
  make_progress_claim,
):
  ctx = verification_admin_context
  project = await project_factory(organization=ctx.organization)
  boq = await make_boq_item(
    organization_id=ctx.organization.id, project_id=project.id
  )
  claim = await make_progress_claim(
    organization_id=ctx.organization.id,
    project_id=project.id,
    boq_item_id=boq.id,
    status=ProgressClaimStatus.DRAFT,
    version=3,
  )

  with pytest.raises(TraceException) as exc:
    await verification_service.update_claim(
      ctx.organization.id,
      claim.id,
      ProgressClaimUpdateRequest(version=1, claimed_quantity=Decimal("9")),
    )
  assert exc.value.code == "CONCURRENT_MODIFICATION"

@pytest.mark.asyncio
async def test_submit_draft_claim(
  verification_service: VerificationService,
  verification_admin_context,
  project_factory,
  make_boq_item,
  make_progress_claim,
):
  ctx = verification_admin_context
  project = await project_factory(organization=ctx.organization)
  boq = await make_boq_item(
    organization_id=ctx.organization.id, project_id=project.id
  )
  claim = await make_progress_claim(
    organization_id=ctx.organization.id,
    project_id=project.id,
    boq_item_id=boq.id,
    status=ProgressClaimStatus.DRAFT,
    version=1,
  )

  with patch.object(
    verification_service.notifications,
    "notify_by_permission",
    new_callable=AsyncMock,
  ) as mock_notify:
    result = await verification_service.submit_claim(
      ctx.organization.id, claim.id, ctx.user.id
    )

  assert result.status == ProgressClaimStatus.SUBMITTED
  assert result.submitted_by == ctx.user.id
  assert result.submitted_at is not None
  assert result.version == 2
  mock_notify.assert_awaited_once()
  call_kwargs = mock_notify.await_args.kwargs
  assert call_kwargs["exclude_user_id"] == ctx.user.id

@pytest.mark.asyncio
async def test_approve_submitted_claim(
  verification_service: VerificationService,
  verification_admin_context,
  project_factory,
  make_boq_item,
  make_progress_claim,
):
  ctx = verification_admin_context
  project = await project_factory(organization=ctx.organization)
  boq = await make_boq_item(
    organization_id=ctx.organization.id, project_id=project.id
  )
  submitter_id = ctx.user.id
  claim = await make_progress_claim(
    organization_id=ctx.organization.id,
    project_id=project.id,
    boq_item_id=boq.id,
    status=ProgressClaimStatus.SUBMITTED,
    version=2,
    submitted_by=submitter_id,
  )

  with (
    patch.object(verification_service.audit, "log", new_callable=AsyncMock) as mock_audit,
    patch.object(
      verification_service.notifications, "notify_user", new_callable=AsyncMock
    ) as mock_notify,
  ):
    result = await verification_service.approve_claim(
      ctx.organization.id,
      claim.id,
      ctx.user.id,
      ProgressClaimReviewRequest(version=2, note="Looks good"),
    )

  assert result.status == ProgressClaimStatus.APPROVED
  assert result.reviewed_by == ctx.user.id
  assert result.review_note == "Looks good"
  assert result.version == 3
  mock_audit.assert_awaited_once()
  mock_notify.assert_awaited_once()
  assert mock_notify.await_args.args[1] == submitter_id

@pytest.mark.asyncio
async def test_approve_wrong_status_or_version(
  verification_service: VerificationService,
  verification_admin_context,
  project_factory,
  make_boq_item,
  make_progress_claim,
):
  ctx = verification_admin_context
  project = await project_factory(organization=ctx.organization)
  boq = await make_boq_item(
    organization_id=ctx.organization.id, project_id=project.id
  )

  draft = await make_progress_claim(
    organization_id=ctx.organization.id,
    project_id=project.id,
    boq_item_id=boq.id,
    status=ProgressClaimStatus.DRAFT,
    version=1,
  )
  with pytest.raises(TraceException) as exc:
    await verification_service.approve_claim(
      ctx.organization.id,
      draft.id,
      ctx.user.id,
      ProgressClaimReviewRequest(version=1),
    )
  assert exc.value.code == "PROGRESS_CLAIM_NOT_SUBMITTED"

  submitted = await make_progress_claim(
    organization_id=ctx.organization.id,
    project_id=project.id,
    boq_item_id=boq.id,
    status=ProgressClaimStatus.SUBMITTED,
    version=5,
  )
  with pytest.raises(TraceException) as exc:
    await verification_service.approve_claim(
      ctx.organization.id,
      submitted.id,
      ctx.user.id,
      ProgressClaimReviewRequest(version=4),
    )
  assert exc.value.code == "CONCURRENT_MODIFICATION"

@pytest.mark.asyncio
async def test_reject_submitted_claim(
  verification_service: VerificationService,
  verification_admin_context,
  project_factory,
  make_boq_item,
  make_progress_claim,
):
  ctx = verification_admin_context
  project = await project_factory(organization=ctx.organization)
  boq = await make_boq_item(
    organization_id=ctx.organization.id, project_id=project.id
  )
  submitter_id = ctx.user.id
  claim = await make_progress_claim(
    organization_id=ctx.organization.id,
    project_id=project.id,
    boq_item_id=boq.id,
    status=ProgressClaimStatus.SUBMITTED,
    version=1,
    submitted_by=submitter_id,
  )

  with (
    patch.object(verification_service.audit, "log", new_callable=AsyncMock) as mock_audit,
    patch.object(
      verification_service.notifications, "notify_user", new_callable=AsyncMock
    ) as mock_notify,
  ):
    result = await verification_service.reject_claim(
      ctx.organization.id,
      claim.id,
      ctx.user.id,
      ProgressClaimReviewRequest(version=1, note="Insufficient evidence"),
    )

  assert result.status == ProgressClaimStatus.REJECTED
  assert result.review_note == "Insufficient evidence"
  assert result.version == 2
  mock_audit.assert_awaited_once()
  mock_notify.assert_awaited_once()
  body = mock_notify.await_args.kwargs.get("body") or mock_notify.await_args.args[3]
  assert "Insufficient evidence" in body

@pytest.mark.asyncio
async def test_create_photo_boq_link_success(
  verification_service: VerificationService,
  verification_admin_context,
  project_factory,
  make_boq_item,
  make_progress_claim,
  make_site_photo,
):
  ctx = verification_admin_context
  project = await project_factory(organization=ctx.organization)
  boq = await make_boq_item(
    organization_id=ctx.organization.id, project_id=project.id
  )
  claim = await make_progress_claim(
    organization_id=ctx.organization.id,
    project_id=project.id,
    boq_item_id=boq.id,
    status=ProgressClaimStatus.DRAFT,
  )
  photo = await make_site_photo(
    organization=ctx.organization, project_id=project.id
  )

  fake_ai_result = MagicMock()
  fake_ai_result.success = True
  fake_ai_result.parsed_output = {
    "tags": [{"tag": "rebar", "confidence": 0.92}],
    "visually_consistent_with_claim": True,
    "notes": "Looks consistent",
  }

  with (
    patch(
      "app.modules.verification.service.download_bytes",
      return_value=b"fake-image-bytes",
    ),
    patch.object(
      verification_service, "_run_photo_tagging", new_callable=AsyncMock
    ) as mock_ai,
    patch.object(
      verification_service, "_apply_ai_tags", new_callable=AsyncMock
    ) as mock_apply,
  ):
    mock_ai.return_value = fake_ai_result

    link = await verification_service.create_photo_boq_link(
      ctx.organization.id,
      ctx.user.id,
      PhotoBOQLinkCreateRequest(
        progress_claim_id=claim.id,
        site_photo_id=photo.id,
        boq_item_id=boq.id,
        note="North elevation",
      ),
    )

  assert link.progress_claim_id == claim.id
  assert link.site_photo_id == photo.id
  assert link.boq_item_id == boq.id
  assert link.created_by == ctx.user.id
  mock_ai.assert_awaited_once()
  mock_apply.assert_awaited_once()

@pytest.mark.asyncio
async def test_create_link_on_approved_claim_rejected(
  verification_service: VerificationService,
  verification_admin_context,
  project_factory,
  make_boq_item,
  make_progress_claim,
  make_site_photo,
):
  ctx = verification_admin_context
  project = await project_factory(organization=ctx.organization)
  boq = await make_boq_item(
    organization_id=ctx.organization.id, project_id=project.id
  )
  claim = await make_progress_claim(
    organization_id=ctx.organization.id,
    project_id=project.id,
    boq_item_id=boq.id,
    status=ProgressClaimStatus.APPROVED,
  )
  photo = await make_site_photo(
    organization=ctx.organization, project_id=project.id
  )

  with pytest.raises(TraceException) as exc:
    await verification_service.create_photo_boq_link(
      ctx.organization.id,
      ctx.user.id,
      PhotoBOQLinkCreateRequest(
        progress_claim_id=claim.id,
        site_photo_id=photo.id,
        boq_item_id=boq.id,
      ),
    )
  assert exc.value.code == "PROGRESS_CLAIM_NOT_EDITABLE"

@pytest.mark.asyncio
async def test_create_link_boq_mismatch(
  verification_service: VerificationService,
  verification_admin_context,
  project_factory,
  make_boq_item,
  make_progress_claim,
  make_site_photo,
):
  ctx = verification_admin_context
  project = await project_factory(organization=ctx.organization)
  boq_claim = await make_boq_item(
    organization_id=ctx.organization.id, project_id=project.id
  )
  boq_other = await make_boq_item(
    organization_id=ctx.organization.id, project_id=project.id
  )
  claim = await make_progress_claim(
    organization_id=ctx.organization.id,
    project_id=project.id,
    boq_item_id=boq_claim.id,
    status=ProgressClaimStatus.DRAFT,
  )
  photo = await make_site_photo(
    organization=ctx.organization, project_id=project.id
  )

  with pytest.raises(TraceException) as exc:
    await verification_service.create_photo_boq_link(
      ctx.organization.id,
      ctx.user.id,
      PhotoBOQLinkCreateRequest(
        progress_claim_id=claim.id,
        site_photo_id=photo.id,
        boq_item_id=boq_other.id,
      ),
    )
  assert exc.value.code == "BOQ_ITEM_MISMATCH"

@pytest.mark.asyncio
async def test_create_link_duplicate_rejected(
  verification_service: VerificationService,
  verification_admin_context,
  project_factory,
  make_boq_item,
  make_progress_claim,
  make_site_photo,
  db_session,
):
  ctx = verification_admin_context
  project = await project_factory(organization=ctx.organization)
  boq = await make_boq_item(
    organization_id=ctx.organization.id, project_id=project.id
  )
  claim = await make_progress_claim(
    organization_id=ctx.organization.id,
    project_id=project.id,
    boq_item_id=boq.id,
    status=ProgressClaimStatus.SUBMITTED,
  )
  photo = await make_site_photo(
    organization=ctx.organization, project_id=project.id
  )

  existing = PhotoBOQLink(
    id=uuid4(),
    organization_id=ctx.organization.id,
    project_id=project.id,
    progress_claim_id=claim.id,
    site_photo_id=photo.id,
    boq_item_id=boq.id,
  )
  db_session.add(existing)
  await db_session.flush()

  with (
    patch("app.modules.verification.service.download_bytes", return_value=b""),
    patch.object(
      verification_service, "_run_photo_tagging", new_callable=AsyncMock
    ) as mock_ai,
  ):
    mock_ai.return_value = MagicMock(success=False, parsed_output=None)

    with pytest.raises(TraceException) as exc:
      await verification_service.create_photo_boq_link(
        ctx.organization.id,
        ctx.user.id,
        PhotoBOQLinkCreateRequest(
          progress_claim_id=claim.id,
          site_photo_id=photo.id,
          boq_item_id=boq.id,
        ),
      )
  assert exc.value.code == "PHOTO_BOQ_LINK_ALREADY_EXISTS"

@pytest.mark.asyncio
async def test_create_link_photo_wrong_project(
  verification_service: VerificationService,
  verification_admin_context,
  project_factory,
  make_boq_item,
  make_progress_claim,
  make_site_photo,
):
  ctx = verification_admin_context
  project_a = await project_factory(organization=ctx.organization)
  project_b = await project_factory(organization=ctx.organization)
  boq = await make_boq_item(
    organization_id=ctx.organization.id, project_id=project_a.id
  )
  claim = await make_progress_claim(
    organization_id=ctx.organization.id,
    project_id=project_a.id,
    boq_item_id=boq.id,
    status=ProgressClaimStatus.DRAFT,
  )
  photo_on_b = await make_site_photo(
    organization=ctx.organization, project_id=project_b.id
  )

  with pytest.raises(TraceException) as exc:
    await verification_service.create_photo_boq_link(
      ctx.organization.id,
      ctx.user.id,
      PhotoBOQLinkCreateRequest(
        progress_claim_id=claim.id,
        site_photo_id=photo_on_b.id,
        boq_item_id=boq.id,
      ),
    )
  assert exc.value.code == "SITE_PHOTO_PROJECT_MISMATCH"
