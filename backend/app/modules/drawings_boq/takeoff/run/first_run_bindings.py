from __future__ import annotations
from app.modules.drawings_boq.takeoff.run import completeness as CR
from app.modules.drawings_boq.takeoff.first_run import job as JB
from app.modules.drawings_boq.takeoff.completeness import facts as F
from app.modules.drawings_boq.takeoff.profile import run as PRUN
from app.modules.drawings_boq.takeoff.profile import convention as CVN
from app.modules.drawings_boq.takeoff.first_run import stages as ST
from app.modules.drawings_boq.takeoff.first_run import report as RP
from app.modules.drawings_boq.takeoff.run import reading_adapter as AD

def offline_bindings(pdfs: list | None = None, plains: list | None = None, lines: list | None = None, page_facts: list | None = None) -> dict:
  def register(state: dict) -> None:
    got = plains if plains is not None else [CR.plain_read(AD.read_items(p)) for p in pdfs or []]
    if not got:
      raise JB.Upstream("no PDF was given")
    state["plain"] = CR.merge(got)
    state["pages"] = CR.page_rows(state["plain"])
    if page_facts is not None:
      state["page_facts"] = page_facts
    elif pdfs:
      state["page_facts"] = [f for n, p in enumerate(pdfs) for f in PRUN.facts_of_pdf(p, n * CR.SHEET_SHIFT)]

  def need(state: dict) -> dict:
    if "plain" not in state:
      raise JB.Upstream("the register stage gave no reading")
    return state["plain"]

  def profile(state: dict) -> None:
    plain = need(state)
    state["facts"] = F.project_facts(state["pages"], state.get("decisions"), state.get("storeys"), CR.join_floors_of(plain))
    if state.get("page_facts"):
      state["convention"] = CVN.build(state["page_facts"], state["pages"])

  def scale(state: dict) -> None:
    plain = need(state)
    pages = list(plain["pages"].values())
    state["scale"] = {"pages": len(pages), "with_scale": sum(1 for p in pages if p.get("mm_per_pt"))}

  def read(state: dict) -> None:
    state["read_counts"] = {"items": len(need(state)["items"]), "pages": len(need(state)["pages"])}

  def members(state: dict) -> None:
    state["evidence"] = CR.evidence_of(need(state), None)

  def quantities(state: dict) -> None:
    if lines is not None and "evidence" in state:
      state["evidence"]["lines"] = [dict(ln) for ln in lines if ln.get("family") and ln.get("value") is not None]
      ST.ledger_stage(state)

  return {"register": register, "profile": profile, "scale": scale, "read": read, "members": members, "ledger": ST.ledger_stage, "quantities": quantities, "self_check": ST.self_check_stage, "boq": ST.boq_stage, "questions": ST.questions_stage}

def run_project(pdfs: list | None = None, plains: list | None = None, lines: list | None = None, storeys: list | None = None, conventions: list | None = None,
  answers: dict | None = None, methods: dict | None = None, progress=None, bindings: dict | None = None) -> tuple:
  state = {"storeys": storeys, "conventions": list(conventions or []), "answers": dict(answers or {}), "methods": dict(methods or {})}
  b = bindings if bindings is not None else offline_bindings(pdfs, plains, lines)
  out = JB.run(b, state, progress=progress)
  return state, out, RP.build(state, out), b
