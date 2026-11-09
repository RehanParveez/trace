from __future__ import annotations
import json
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.core.exceptions import TraceException
from app.modules.drawings_boq.takeoff.extract import finish_rules as FR
from app.engine.measure import rulebook as RB
from app.engine.measure import company as CO
from app.engine.measure import readings as QS
from app.engine.catalogue import methods_qs as MQ
from app.modules.drawings_boq import rule_book_service as RBS

IN_FORCE, SAME, WOULD_CHANGE, KEPT, NOT_SETTABLE = "IN_FORCE", "SAME_AS_TRACE", "WOULD_CHANGE", "YOURS", "NOT_SETTABLE"

class MethodRow(BaseModel):
  id: str
  aspect: str
  item: str
  says: str
  key: str
  scope: dict = Field(default_factory=dict)
  value: object
  trace_value: object = Field(default=None, description="What Trace does when the company has set nothing.")
  held_value: object = Field(default=None, description="What the company's rule book holds now for this rule.")
  held_origin: str | None = None
  state: str = Field(description="IN_FORCE (the company's book holds it), SAME_AS_TRACE (Trace already does it, so choosing the profile only pins it), WOULD_CHANGE, YOURS (the company set its own figure, which choosing keeps) or NOT_SETTABLE (a rule that is decided for each drawing, shown for the record).")
  source: str
  confirmed: bool = Field(description="True for a recorded answer of the QS; False for a figure read from his workbook that he has not confirmed.")

class OpenQuestion(BaseModel):
  id: str
  aspect: str
  item: str
  question: str
  trace: str
  standard: str | None = None
  asked: str | None = None

class ProfileView(BaseModel):
  id: str
  label: str
  qs: str
  chosen: bool
  methods: list[MethodRow]
  would_change: int
  same_as_trace: int
  kept: int
  not_settable: int
  unconfirmed: int = Field(description="Methods read from his workbook that he has not confirmed as his own.")

class QsMethodsResponse(BaseModel):
  chosen: str | None = Field(description="The profile the company measures by; None means Trace's default.")
  profiles: list[ProfileView]
  open_questions: list[OpenQuestion]

class QsMethodChoice(BaseModel):
  profile: str | None = Field(default=None, description="A profile id, or null for Trace's default.")
  note: str | None = Field(default=None, max_length=500)

class QsMethodResult(BaseModel):
  chosen: str | None
  written: int = Field(description="Rules the company's book now holds from the profile.")
  removed: int = Field(description="Rules taken out of the book because they were the profile's and nothing else had changed them.")
  kept: list[str] = Field(description="Rules the company had set itself; they were not changed.")
  not_settable: list[str]

def _scope_key(scope) -> str:
  return json.dumps(scope or {}, sort_keys=True)

def settable(key: str) -> bool:
  if key in FR.KEYS:
    return True
  return any(r["key"] == key and r["editable"] for r in QS.registry())

def trace_default(key: str, scope: dict | None = None):
  for r in QS.registry():
    if r["key"] == key:
      return r["default"]
  seed = RB.SEED.get(key)
  return None if seed is None or key == "finish.strip_widths_mm" else seed.value

def same_value(a, b) -> bool:
  if isinstance(a, dict) or isinstance(b, dict):
    return isinstance(a, dict) and isinstance(b, dict) and a.keys() == b.keys() and all(same_value(a[k], b[k]) for k in a)
  try:
    return abs(float(a) - float(b)) <= 1e-9
  except (TypeError, ValueError):
    return str(a).strip().upper() == str(b).strip().upper()

def held_index(rows) -> dict:
  return {(r["key"], _scope_key(r.get("scope"))): (r["value"], r["origin"]) for r in rows if r.get("value") is not None}

def state_of(rule: dict, held: dict) -> str:
  if not settable(rule["key"]):
    return NOT_SETTABLE
  got = held.get((rule["key"], _scope_key(rule["scope"])))
  if got is not None:
    if got[1] == CO.COMPANY and not same_value(got[0], rule["value"]):
      return KEPT
    if got[1] == CO.QS_WORKBOOK and same_value(got[0], rule["value"]):
      return IN_FORCE
  if same_value(trace_default(rule["key"], rule["scope"]), rule["value"]):
    return SAME
  return WOULD_CHANGE

def plan(profile_id: str, held: dict) -> dict:
  write, kept, not_settable = [], [], []
  for rule in MQ.rules(profile_id):
    st = state_of(rule, held)
    
    if st == NOT_SETTABLE:
      not_settable.append(rule["id"])
    elif st == KEPT:
      kept.append(rule["id"])
    elif st != IN_FORCE:
      write.append({"key": rule["key"], "scope": rule["scope"], "value": rule["value"], "origin": CO.QS_WORKBOOK, "cls": RB.JUDGEMENT, "note": rule["note"]})
  if held.get((MQ.MARKER_KEY, "{}")) is None or held[(MQ.MARKER_KEY, "{}")][0] != profile_id:
    write.append({"key": MQ.MARKER_KEY, "scope": {}, "value": profile_id, "origin": CO.QS_WORKBOOK, "cls": RB.JUDGEMENT, "note": f"The company measures the way {MQ.profile(profile_id)['qs']} does."})
  return {"write": write, "kept": kept, "not_settable": not_settable}

def plan_off(held: dict) -> dict:
  chosen = (held.get((MQ.MARKER_KEY, "{}")) or (None, None))[0]
  remove = []
  
  if chosen and MQ.profile(chosen) is not None:
    for rule in MQ.rules(chosen):
      got = held.get((rule["key"], _scope_key(rule["scope"])))
      if got is not None and got[1] == CO.QS_WORKBOOK and same_value(got[0], rule["value"]):
        remove.append({"key": rule["key"], "scope": rule["scope"], "value": None, "origin": CO.QS_WORKBOOK})
  if chosen:
    remove.append({"key": MQ.MARKER_KEY, "scope": {}, "value": None, "origin": CO.QS_WORKBOOK})
  return {"remove": remove, "chosen": chosen}

def view(rows, chosen: str | None) -> QsMethodsResponse:
  held = held_index(rows)
  profiles = []
  for p in MQ.profiles():
    methods = []
    
    for rule in MQ.rules(p["id"]):
      got = held.get((rule["key"], _scope_key(rule["scope"])))
      methods.append(MethodRow(id=rule["id"], aspect=rule["aspect"], item=rule["item"], says=rule["says"], key=rule["key"], scope=rule["scope"], value=rule["value"],
        trace_value=trace_default(rule["key"], rule["scope"]), held_value=None if got is None else got[0], held_origin=None if got is None else got[1], state=state_of(rule, held),
        source=rule["source"], confirmed=rule["confirmed"]))
    count = lambda s: sum(1 for m in methods if m.state == s)
    profiles.append(ProfileView(id=p["id"], label=p["label"], qs=p["qs"], chosen=p["id"] == chosen, methods=methods, would_change=count(WOULD_CHANGE), same_as_trace=count(SAME),
      kept=count(KEPT), not_settable=count(NOT_SETTABLE), unconfirmed=sum(1 for m in methods if not m.confirmed)))
  return QsMethodsResponse(chosen=chosen, profiles=profiles, open_questions=[OpenQuestion(**o) for o in MQ.open_questions()])

class QsMethodService:
  def __init__(self, session: AsyncSession):
    self.session = session

  async def _rows(self, organization_id: UUID) -> list:
    book = await RBS.active_book(self.session, organization_id)
    return [] if book is None else [RBS.row_of(r) for r in await RBS.rules_of(self.session, book.id)]

  async def view(self, organization_id: UUID) -> QsMethodsResponse:
    rows = await self._rows(organization_id)
    held = held_index(rows)
    chosen = (held.get((MQ.MARKER_KEY, "{}")) or (None, None))[0]
    return view(rows, chosen if chosen and MQ.profile(chosen) is not None else None)

  async def choose(self, organization_id: UUID, payload: QsMethodChoice) -> QsMethodResult:
    if payload.profile is not None and MQ.profile(payload.profile) is None:
      raise TraceException(f"'{payload.profile}' is not a QS method profile.", status_code=422, code="QS_METHOD_UNKNOWN")
    held = held_index(await self._rows(organization_id))
    
    if payload.profile is None:
      off = plan_off(held)
      if off["remove"]:
        await RBS.publish(self.session, organization_id, off["remove"], note=payload.note or "The company measures with Trace's default again.")
      await self.session.commit()
      return QsMethodResult(chosen=None, written=0, removed=max(0, len(off["remove"]) - (1 if off["chosen"] else 0)), kept=[], not_settable=[])
    
    todo = plan(payload.profile, held)
    for ch in todo["write"]:
      if ch["key"] != MQ.MARKER_KEY:
        ch["value"] = RBS.checked_value(ch["key"], ch["value"], ch["scope"])
    if todo["write"]:
      await RBS.publish(self.session, organization_id, todo["write"], note=payload.note)
    await self.session.commit()
    return QsMethodResult(chosen=payload.profile, written=sum(1 for c in todo["write"] if c["key"] != MQ.MARKER_KEY), removed=0, kept=todo["kept"], not_settable=todo["not_settable"])
