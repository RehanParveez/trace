from __future__ import annotations
from datetime import date
from decimal import Decimal as D
from uuid import uuid4
import pytest
from sqlalchemy import select
from app.core.exceptions import TraceException
from app.modules.audit.models import AuditEntityType, AuditLog
from app.modules.drawings_boq.models import RateBook, RateItem
from app.modules.drawings_boq.pricing.rate_service import RateBookService
from app.modules.drawings_boq.pricing.schemas import (
  AnalysisComponentInput, AnalysisCreateRequest, AnalysisUpdateRequest, EscalationCreateRequest, OverrideCreateRequest,
  RateBookCreateRequest, RateBookUpdateRequest, RateItemInput, RateItemUpdateRequest,
)

def _svc(s):
  return RateBookService(s)

def _item(code="CONC-COL", unit="m3", rate="20000", **kw):
  return RateItemInput(work_item_code=code, unit=unit, rate=D(rate), **kw)

async def _draft_with_rates(db_session, org, actor, code="MY-RATES", rates=(("CONC-COL", "m3", "20000"),)):
  svc = _svc(db_session)
  book = await svc.create_book(org.id, actor.user_id, RateBookCreateRequest(code=code, name="Mine"))
  for r in rates:
    await svc.add_item(org.id, actor.user_id, book.id, _item(*r))
  return book

async def _err(coro, code, status=None):
  with pytest.raises(TraceException) as exc:
    await coro
  assert exc.value.code == code
  if status:
    assert exc.value.status_code == status
  return exc.value

async def test_create_book_defaults_and_version_increment(db_session, organization, actor_a):
  svc = _svc(db_session)
  b1 = await svc.create_book(organization.id, actor_a.user_id, RateBookCreateRequest(code="my-rates", name=" Mine "))
  assert (b1.code, b1.name, b1.status, b1.immutable_version, b1.organization_id) == ("MY-RATES", "Mine", "DRAFT", 1, organization.id)
  assert b1.item_count == 0
  b2 = await svc.create_book(organization.id, actor_a.user_id, RateBookCreateRequest(code="MY-RATES", name="Mine again"))
  assert b2.immutable_version == 2

async def test_create_book_audited(db_session, organization, actor_a):
  book = await _svc(db_session).create_book(organization.id, actor_a.user_id, RateBookCreateRequest(code="A", name="A"))
  row = (await db_session.execute(select(AuditLog).where(AuditLog.entity_id == book.id))).scalar_one()
  assert row.entity_type == AuditEntityType.RATE_BOOK and "Created rate book A v1" in row.summary

async def test_copy_system_book_into_org_copies_items_and_escalations(db_session, organization, actor_a, make_book):
  system = await make_book(None, "PUNJAB_CSR", rates=[("CONC-COL", "m3", 21000, "Concrete"), ("STEEL-60", "kg", 280, "Steel")],
    escalations=[("ALL", date(2026, 7, 1), "1.06")])
  svc = _svc(db_session)
  mine = await svc.create_book(organization.id, actor_a.user_id,
    RateBookCreateRequest(code="OUR_RATES", name="Ours", copy_from_id=system.id))
  assert mine.item_count == 2 and mine.escalation_count == 1 and mine.parent_rate_book_id == system.id
  items, _ = await svc.list_items(organization.id, mine.id, q=None, trade=None, only_active=True, after=None, limit=10)
  assert {(i.work_item_code, i.organization_id) for i in items} == {("CONC-COL", organization.id), ("STEEL-60", organization.id)}
  assert (await db_session.get(RateBook, system.id)).status == "ACTIVE"          # source untouched

async def test_system_book_is_read_only_for_tenants(db_session, organization, actor_a, make_book):
  system = await make_book(None, "PUNJAB_CSR", rates=[("CONC-COL", "m3", 21000)])
  svc = _svc(db_session)
  await _err(svc.update_book(organization.id, actor_a.user_id, system.id, RateBookUpdateRequest(name="x")), "RATE_BOOK_READ_ONLY", 403)
  await _err(svc.add_item(organization.id, actor_a.user_id, system.id, _item("X", "m3", "1")), "RATE_BOOK_READ_ONLY", 403)
  await _err(svc.publish_book(organization.id, actor_a.user_id, system.id), "RATE_BOOK_READ_ONLY", 403)
  await _err(svc.delete_book(organization.id, actor_a.user_id, system.id), "RATE_BOOK_READ_ONLY", 403)
  await _err(svc.add_escalation(organization.id, actor_a.user_id, system.id,
    EscalationCreateRequest(effective_from=date(2026, 1, 1), factor=D("1.1"))), "RATE_BOOK_READ_ONLY", 403)
  assert (await svc.get_book(organization.id, system.id)).item_count == 1       # but readable

async def test_other_org_book_is_invisible(db_session, organization, other_organization, actor_a, make_book):
  theirs = await make_book(other_organization, "THEIRS", rates=[("A", "m3", 1)])
  svc = _svc(db_session)
  await _err(svc.get_book(organization.id, theirs.id), "RATE_BOOK_NOT_FOUND", 404)
  rows, _ = await svc.list_books(organization.id, status=None, owner="all", after=None, limit=50)
  assert theirs.id not in {b.id for b in rows}

async def test_update_book_only_while_draft_and_validates_dates(db_session, organization, actor_a):
  svc = _svc(db_session)
  book = await _draft_with_rates(db_session, organization, actor_a)
  upd = await svc.update_book(organization.id, actor_a.user_id, book.id, RateBookUpdateRequest(name="New", edition="2026", currency="usd"))
  assert (upd.name, upd.edition, upd.currency) == ("New", "2026", "USD")
  await _err(svc.update_book(organization.id, actor_a.user_id, book.id,
    RateBookUpdateRequest(effective_from=date(2026, 5, 1), effective_to=date(2026, 1, 1))), "INVALID_EFFECTIVE_RANGE", 422)
  await svc.publish_book(organization.id, actor_a.user_id, book.id)
  await _err(svc.update_book(organization.id, actor_a.user_id, book.id, RateBookUpdateRequest(name="x")), "RATE_BOOK_IMMUTABLE", 409)

async def test_publish_requires_rates_sets_hash_and_supersedes_previous(db_session, organization, actor_a):
  svc = _svc(db_session)
  empty = await svc.create_book(organization.id, actor_a.user_id, RateBookCreateRequest(code="BK", name="Empty"))
  await _err(svc.publish_book(organization.id, actor_a.user_id, empty.id), "RATE_BOOK_EMPTY", 422)
  await svc.add_item(organization.id, actor_a.user_id, empty.id, _item())
  v1 = await svc.publish_book(organization.id, actor_a.user_id, empty.id)
  assert v1.status == "ACTIVE" and v1.published_at is not None and len(v1.content_hash) == 64
  v2 = await svc.new_version(organization.id, actor_a.user_id, v1.id)
  assert v2.status == "DRAFT" and v2.immutable_version == 2 and v2.parent_rate_book_id == v1.id and v2.item_count == 1
  await svc.update_item(organization.id, actor_a.user_id,
    (await svc.list_items(organization.id, v2.id, q=None, trade=None, only_active=True, after=None, limit=5))[0][0].id,
    RateItemUpdateRequest(rate=D("22000")))
  v2p = await svc.publish_book(organization.id, actor_a.user_id, v2.id)
  assert v2p.supersedes_rate_book_id == v1.id and v2p.content_hash != v1.content_hash
  assert (await db_session.get(RateBook, v1.id)).status == "SUPERSEDED"

async def test_published_book_items_are_frozen(db_session, organization, actor_a):
  svc = _svc(db_session)
  book = await _draft_with_rates(db_session, organization, actor_a)
  item = (await svc.list_items(organization.id, book.id, q=None, trade=None, only_active=True, after=None, limit=5))[0][0]
  await svc.publish_book(organization.id, actor_a.user_id, book.id)
  await _err(svc.add_item(organization.id, actor_a.user_id, book.id, _item("B", "m2", "1")), "RATE_BOOK_IMMUTABLE", 409)
  await _err(svc.update_item(organization.id, actor_a.user_id, item.id, RateItemUpdateRequest(rate=D("1"))), "RATE_BOOK_IMMUTABLE", 409)
  await _err(svc.delete_item(organization.id, actor_a.user_id, item.id), "RATE_BOOK_IMMUTABLE", 409)
  await _err(svc.delete_book(organization.id, actor_a.user_id, book.id), "RATE_BOOK_IMMUTABLE", 409)

async def test_new_version_of_draft_rejected_and_archive_rules(db_session, organization, actor_a):
  svc = _svc(db_session)
  book = await _draft_with_rates(db_session, organization, actor_a)
  await _err(svc.new_version(organization.id, actor_a.user_id, book.id), "RATE_BOOK_IS_DRAFT", 409)
  await _err(svc.archive_book(organization.id, actor_a.user_id, book.id), "INVALID_RATE_BOOK_STATE", 409)
  pub = await svc.publish_book(organization.id, actor_a.user_id, book.id)
  assert (await svc.archive_book(organization.id, actor_a.user_id, pub.id)).status == "ARCHIVED"

async def test_delete_draft_book_removes_children(db_session, organization, actor_a):
  svc = _svc(db_session)
  book = await _draft_with_rates(db_session, organization, actor_a)
  await svc.delete_book(organization.id, actor_a.user_id, book.id)
  assert (await db_session.execute(select(RateItem).where(RateItem.rate_book_id == book.id))).first() is None
  await _err(svc.get_book(organization.id, book.id), "RATE_BOOK_NOT_FOUND", 404)

async def test_list_books_filters_and_keyset_pagination(db_session, organization, actor_a, make_book):
  svc = _svc(db_session)
  await make_book(None, "SYS-A", rates=[("A", "m3", 1)])
  for code in ("ORG-1", "ORG-2", "ORG-3"):
    await make_book(organization, code, rates=[("A", "m3", 1)], status="DRAFT")
  rows, nxt = await svc.list_books(organization.id, status=None, owner="org", after=None, limit=2)
  assert [b.code for b in rows] == ["ORG-1", "ORG-2"] and nxt == rows[-1].id
  rest, nxt2 = await svc.list_books(organization.id, status=None, owner="org", after=nxt, limit=2)
  assert [b.code for b in rest] == ["ORG-3"] and nxt2 is None
  sys_rows, _ = await svc.list_books(organization.id, status="ACTIVE", owner="system", after=None, limit=50)
  assert [b.code for b in sys_rows] == ["SYS-A"]

async def test_items_unique_per_code_and_unit_and_units_normalised(db_session, organization, actor_a):
  svc = _svc(db_session)
  book = await svc.create_book(organization.id, actor_a.user_id, RateBookCreateRequest(code="U", name="U"))
  first = await svc.add_item(organization.id, actor_a.user_id, book.id, _item("c-1", "CUM", "100"))
  assert (first.work_item_code, first.unit) == ("C-1", "m3")
  await svc.add_item(organization.id, actor_a.user_id, book.id, _item("C-1", "cft", "3"))
  await _err(svc.add_item(organization.id, actor_a.user_id, book.id, _item("C-1", "m3", "5")), "RATE_ITEM_EXISTS", 409)

async def test_bulk_upsert_creates_updates_and_rejects_duplicates(db_session, organization, actor_a):
  svc = _svc(db_session)
  book = await _draft_with_rates(db_session, organization, actor_a)
  res = await svc.bulk_upsert(organization.id, actor_a.user_id, book.id,
    [_item("CONC-COL", "m3", "21000.50", trade="Concrete"), _item("STEEL", "kg", "290")])
  assert res == {"created": 1, "updated": 1, "total": 2}
  items, _ = await svc.list_items(organization.id, book.id, q="conc", trade=None, only_active=True, after=None, limit=10)
  assert items[0].rate == D("21000.50") and items[0].trade == "Concrete"
  await _err(svc.bulk_upsert(organization.id, actor_a.user_id, book.id, [_item("A", "m3", "1"), _item("a", "CUM", "2")]),
    "RATE_IMPORT_DUPLICATE", 422)

async def test_csv_import_all_or_nothing(db_session, organization, actor_a):
  svc = _svc(db_session)
  book = await svc.create_book(organization.id, actor_a.user_id, RateBookCreateRequest(code="CSV", name="CSV"))
  good = b"\xef\xbb\xbfWork_Item_Code,Unit,Rate,Trade,csr_ref\nCONC-COL,cum,\"21,500.00\",Concrete,CSR-4.1\n\nSTEEL,kg,285,,\n"
  assert await svc.import_csv(organization.id, actor_a.user_id, book.id, good) == {"created": 2, "updated": 0, "total": 2}
  items, _ = await svc.list_items(organization.id, book.id, q=None, trade=None, only_active=True, after=None, limit=10)
  conc = next(i for i in items if i.work_item_code == "CONC-COL")
  assert (conc.unit, conc.rate, conc.csr_ref) == ("m3", D("21500.00"), "CSR-4.1")
  bad = b"work_item_code,unit,rate\nA,m3,abc\nB,m3,-5\nC,m3,10\n"
  e = await _err(svc.import_csv(organization.id, actor_a.user_id, book.id, bad), "RATE_IMPORT_INVALID", 422)
  assert "row 2" in e.message and "row 3" in e.message
  assert len((await svc.list_items(organization.id, book.id, q=None, trade=None, only_active=True, after=None, limit=10))[0]) == 2
  await _err(svc.import_csv(organization.id, actor_a.user_id, book.id, b"code,unit\nA,m3\n"), "RATE_IMPORT_INVALID", 422)
  await _err(svc.import_csv(organization.id, actor_a.user_id, book.id, b"work_item_code,unit,rate\n"), "RATE_IMPORT_INVALID", 422)
  await _err(svc.import_csv(organization.id, actor_a.user_id, book.id, b"\xff\xfe\x00"), "RATE_IMPORT_INVALID", 422)

async def test_item_listing_filters_and_pagination(db_session, organization, actor_a):
  svc = _svc(db_session)
  book = await svc.create_book(organization.id, actor_a.user_id, RateBookCreateRequest(code="L", name="L"))
  await svc.bulk_upsert(organization.id, actor_a.user_id, book.id,
    [_item(f"W-{n:02d}", "m3", str(n), trade="Concrete" if n % 2 else "Steel") for n in range(1, 8)])
  page1, nxt = await svc.list_items(organization.id, book.id, q=None, trade=None, only_active=True, after=None, limit=3)
  assert [i.work_item_code for i in page1] == ["W-01", "W-02", "W-03"]
  page2, nxt = await svc.list_items(organization.id, book.id, q=None, trade=None, only_active=True, after=nxt, limit=3)
  page3, nxt = await svc.list_items(organization.id, book.id, q=None, trade=None, only_active=True, after=nxt, limit=3)
  assert [i.work_item_code for i in page2 + page3] == [f"W-{n:02d}" for n in range(4, 8)] and nxt is None
  steel, _ = await svc.list_items(organization.id, book.id, q=None, trade="steel", only_active=True, after=None, limit=10)
  assert [i.work_item_code for i in steel] == ["W-02", "W-04", "W-06"]
  off = await svc.update_item(organization.id, actor_a.user_id, steel[0].id, RateItemUpdateRequest(is_active=False))
  assert off.is_active is False
  assert len((await svc.list_items(organization.id, book.id, q=None, trade="steel", only_active=True, after=None, limit=10))[0]) == 2
  assert len((await svc.list_items(organization.id, book.id, q=None, trade="steel", only_active=False, after=None, limit=10))[0]) == 3

async def test_escalations_on_draft_and_active_but_not_archived(db_session, organization, actor_a):
  svc = _svc(db_session)
  book = await _draft_with_rates(db_session, organization, actor_a)
  e1 = await svc.add_escalation(organization.id, actor_a.user_id, book.id,
    EscalationCreateRequest(trade_scope="all", effective_from=date(2026, 7, 1), factor=D("1.05"), note="Q3 index"))
  assert e1.trade_scope == "ALL" and e1.factor == D("1.05")
  await _err(svc.add_escalation(organization.id, actor_a.user_id, book.id,
    EscalationCreateRequest(effective_from=date(2026, 7, 1), factor=D("1.07"))), "ESCALATION_EXISTS", 409)
  await svc.publish_book(organization.id, actor_a.user_id, book.id)
  e2 = await svc.add_escalation(organization.id, actor_a.user_id, book.id,
    EscalationCreateRequest(trade_scope="Steel", effective_from=date(2026, 8, 1), factor=D("1.2")))
  assert [e.id for e in await svc.list_escalations(organization.id, book.id)] == [e1.id, e2.id]
  await svc.delete_escalation(organization.id, actor_a.user_id, e2.id)
  await svc.archive_book(organization.id, actor_a.user_id, book.id)
  await _err(svc.add_escalation(organization.id, actor_a.user_id, book.id,
    EscalationCreateRequest(effective_from=date(2026, 9, 1), factor=D("1.1"))), "RATE_BOOK_IMMUTABLE", 409)
  await _err(svc.delete_escalation(organization.id, actor_a.user_id, uuid4()), "ESCALATION_NOT_FOUND", 404)

def test_escalation_schema_rejects_non_positive_factor():
  with pytest.raises(ValueError):
    EscalationCreateRequest(effective_from=date(2026, 1, 1), factor=D("0"))

def _comp(**kw):
  base = dict(component_type="MATERIAL", description="Cement", unit="bag", coefficient=D("8"), rate_source="DIRECT", unit_rate=D("1450"))
  base.update(kw)
  return AnalysisComponentInput(**base)

async def test_analysis_compute_and_apply_makes_a_rate_item(db_session, organization, actor_a):
  svc = _svc(db_session)
  book = await svc.create_book(organization.id, actor_a.user_id, RateBookCreateRequest(code="AN", name="AN"))
  a = await svc.create_analysis(organization.id, actor_a.user_id, book.id, AnalysisCreateRequest(
    code="an-col", work_item_code="conc-col", description="Concrete column", unit="m3", overhead_pct=D("10"), profit_pct=D("15"),
    components=[_comp(), _comp(description="Sand", unit="cft", coefficient=D("22.5"), unit_rate=D("85")),
      _comp(component_type="LABOUR", description="Mason", unit="day", coefficient=D("1.5"), unit_rate=D("2200"))]))
  assert a.code == "AN-COL" and a.work_item_code == "CONC-COL" and len(a.components) == 3 and a.computed_rate is None
  computed = await svc.compute_analysis(organization.id, actor_a.user_id, a.id)
  assert computed.computed_rate == D("21267.81") and computed.computed_at is not None
  item = await svc.apply_analysis(organization.id, actor_a.user_id, a.id)
  assert (item.work_item_code, item.unit, item.rate, item.analysis_id) == ("CONC-COL", "m3", D("21267.81"), a.id)
  again = await svc.update_analysis(organization.id, actor_a.user_id, a.id, AnalysisUpdateRequest(profit_pct=D("0")))
  assert again.computed_rate is None                                   # edits invalidate the stored rate
  item2 = await svc.apply_analysis(organization.id, actor_a.user_id, a.id)
  assert item2.id == item.id and item2.rate == D("18493.75")           # 16812.50 direct + 10% overhead, no profit

async def test_analysis_rules(db_session, organization, actor_a):
  svc = _svc(db_session)
  book = await svc.create_book(organization.id, actor_a.user_id, RateBookCreateRequest(code="AR", name="AR"))
  mk = lambda comps: AnalysisCreateRequest(code="X1", work_item_code="W", description="d", unit="m3", components=comps)
  empty = await svc.create_analysis(organization.id, actor_a.user_id, book.id, mk([]))
  await _err(svc.compute_analysis(organization.id, actor_a.user_id, empty.id), "ANALYSIS_EMPTY", 422)
  await _err(svc.create_analysis(organization.id, actor_a.user_id, book.id, mk([_comp()])), "RATE_ANALYSIS_EXISTS", 409)
  filled = await svc.update_analysis(organization.id, actor_a.user_id, empty.id, AnalysisUpdateRequest(components=[_comp()]))
  bd = await svc.breakdown(organization.id, filled)
  assert bd["cost"] == "11600.00" and bd["total"] == "11600.00" and bd["rate_value"] == D("11600.00")
  await svc.delete_analysis(organization.id, actor_a.user_id, empty.id)
  await _err(svc.compute_analysis(organization.id, actor_a.user_id, empty.id), "RATE_ANALYSIS_NOT_FOUND", 404)

async def test_analysis_rate_item_component_pulls_from_book(db_session, organization, actor_a):
  svc = _svc(db_session)
  book = await svc.create_book(organization.id, actor_a.user_id, RateBookCreateRequest(code="AN2", name="AN2"))
  cement = await svc.add_item(organization.id, actor_a.user_id, book.id, _item("CEMENT", "bag", "1500"))
  a = await svc.create_analysis(organization.id, actor_a.user_id, book.id, AnalysisCreateRequest(
    code="MIX", work_item_code="MIX-1", description="Mix", unit="m3",
    components=[AnalysisComponentInput(component_type="MATERIAL", description="Cement", unit="bag", coefficient=D("7"),
      rate_source="RATE_ITEM", ref_rate_item_id=cement.id)]))
  assert (await svc.compute_analysis(organization.id, actor_a.user_id, a.id)).computed_rate == D("10500.00")

async def test_analysis_basis_quantity_divides_total(db_session, organization, actor_a):
  svc = _svc(db_session)
  book = await svc.create_book(organization.id, actor_a.user_id, RateBookCreateRequest(code="AN3", name="AN3"))
  a = await svc.create_analysis(organization.id, actor_a.user_id, book.id, AnalysisCreateRequest(
    code="B", work_item_code="B1", description="per 10", unit="m2", basis_quantity=D("10"), components=[_comp()]))
  assert (await svc.compute_analysis(organization.id, actor_a.user_id, a.id)).computed_rate == D("1160.00")

def _ov(**kw):
  base = dict(work_item_code="conc-col", unit="cum", rate=D("19000"), reason="Negotiated with supplier")
  base.update(kw)
  return OverrideCreateRequest(**base)

async def test_override_lifecycle(db_session, organization, actor_a, project_a):
  svc = _svc(db_session)
  o = await svc.create_override(organization.id, actor_a.user_id, project_a.id, _ov())
  assert (o.work_item_code, o.unit, o.revoked_at) == ("CONC-COL", "m3", None)
  await _err(svc.create_override(organization.id, actor_a.user_id, project_a.id, _ov()), "RATE_OVERRIDE_EXISTS", 409)
  rows, nxt = await svc.list_overrides(organization.id, project_a.id, include_revoked=False, after=None, limit=10)
  assert [x.id for x in rows] == [o.id] and nxt is None
  await _err(svc.revoke_override(organization.id, actor_a.user_id, o.id, "  "), "OVERRIDE_REQUIRES_REASON", 422)
  revoked = await svc.revoke_override(organization.id, actor_a.user_id, o.id, "Supplier changed price")
  assert revoked.revoked_at is not None and revoked.revoke_reason == "Supplier changed price"
  assert revoked.revoked_by_user_id == actor_a.user_id
  await _err(svc.revoke_override(organization.id, actor_a.user_id, o.id, "again"), "RATE_OVERRIDE_REVOKED", 409)
  assert (await svc.list_overrides(organization.id, project_a.id, include_revoked=False, after=None, limit=10))[0] == []
  assert len((await svc.list_overrides(organization.id, project_a.id, include_revoked=True, after=None, limit=10))[0]) == 1
  again = await svc.create_override(organization.id, actor_a.user_id, project_a.id, _ov())      # allowed after revoke
  assert again.id != o.id

def test_override_reason_required():
  with pytest.raises(ValueError):
    _ov(reason="")

async def test_override_on_other_orgs_project_is_404(db_session, organization, actor_a, project_b):
  await _err(_svc(db_session).create_override(organization.id, actor_a.user_id, project_b.id, _ov()), "PROJECT_NOT_FOUND", 404)

async def test_override_not_found_for_other_org(db_session, organization, actor_a):
  await _err(_svc(db_session).revoke_override(organization.id, actor_a.user_id, uuid4(), "x"), "RATE_OVERRIDE_NOT_FOUND", 404)