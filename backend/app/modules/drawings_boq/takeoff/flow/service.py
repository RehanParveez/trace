from __future__ import annotations
from datetime import datetime, timezone
from app.modules.drawings_boq.pricing.priced.service import PricedService, priced_view
from uuid import UUID
from app.modules.identity.models import Organization
from sqlalchemy import select
from app.core.exceptions import TraceException
from app.modules.drawings_boq.pricing.billing import profiles as P
from app.modules.drawings_boq.takeoff.flow import sitting as SIT
from app.modules.drawings_boq.models import CalculationRun
from app.modules.drawings_boq.takeoff.first_run import service as FRS
from app.modules.drawings_boq.takeoff.review.service import ReviewService
from app.modules.drawings_boq.pricing.priced import export as X
from app.modules.drawings_boq.takeoff.flow import documents as DOC
from app.modules.drawings_boq.takeoff.flow import marks as MK
from app.modules.drawings_boq.takeoff.questions import answers as AN
from app.modules.projects.models import Project

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
PDF = "application/pdf"
KINDS = {"xlsx": (XLSX, "xlsx", "priced-boq"), "priced_pdf": (PDF, "pdf", "priced-boq"), "client_pdf": (PDF, "pdf", "client-report")}
FAILED_RUN = ("FAILED", "CANCELLED")
WAITING_RUN = ("QUEUED", "RUNNING", "STAGED", "PROMOTED")

class FlowService(PricedService):
  async def _company_profile(self, org: UUID) -> str | None:
    return (await self.session.execute(select(Organization.billing_profile).where(Organization.id == org))).scalar_one_or_none()

  async def _profile(self, org: UUID, requested: str | None) -> tuple:
    if requested and requested not in P.all_profiles():
      raise TraceException(f"'{requested}' is not a billing profile.", status_code=422, code="PROFILE_UNKNOWN")
    company = await self._company_profile(org)
    profile = P.choose(requested, company)
    source = "REQUEST" if requested else ("COMPANY" if company and company == profile.id else "DEFAULT")
    return profile, source

  async def _held(self, org: UUID, project_id: UUID) -> list:
    drawings = await self.repo.project_pdf_drawings(org, project_id)
    if not drawings:
      raise TraceException("This project has no PDF drawings to read.", status_code=409, code="NO_PDF")
    return drawings

  async def record(self, org: UUID, project_id: UUID, event: str, detail: dict | None = None) -> None:
    drawings = await self._held(org, project_id)
    meta = dict(drawings[0].ingestion_meta or {})
    meta[SIT.KEY] = SIT.mark(meta.get(SIT.KEY), event, datetime.now(timezone.utc), detail)
    drawings[0].ingestion_meta = meta
    await self.session.commit()

  async def _run_step(self, org: UUID, project_id: UUID) -> dict:
    run = (await self.session.execute(select(CalculationRun).where(CalculationRun.organization_id == org, CalculationRun.project_id == project_id)
      .order_by(CalculationRun.created_at.desc()).limit(1))).scalars().first()
    if run is None:
      return {"key": "quantities", "state": "OPEN", "detail": "No calculation run yet."}
    if run.status == "COMPLETED":
      return {"key": "quantities", "state": "DONE", "detail": f"Run completed {run.completed_at.isoformat() if run.completed_at else ''}".strip()}
    if run.status in FAILED_RUN:
      return {"key": "quantities", "state": "FAILED", "detail": run.error_message or run.status}
    return {"key": "quantities", "state": "RUNNING" if run.status in WAITING_RUN else "OPEN", "detail": f"{run.status}, {run.progress_pct}%"}

  async def status(self, org: UUID, project_id: UUID, requested: str | None = None) -> dict:
    profile, source = await self._profile(org, requested)
    drawings = await self.repo.project_pdf_drawings(org, project_id)
    meta = dict(drawings[0].ingestion_meta or {}) if drawings else {}
    sitting = meta.get(SIT.KEY) or {}
    report = meta.get(FRS.META_REPORT) or {}
    held = [d for d in drawings if (d.ingestion_meta or {}).get(AN.META_LEDGER)]
    
    steps = [{"key": "upload", "state": "DONE" if drawings else "OPEN", "detail": f"{len(drawings)} PDF drawing(s)"}]
    if held:
      failed = report.get("failed") or []
      steps.append({"key": "read", "state": "FAILED" if failed else "DONE", "detail": ("Stages failed: " + ", ".join(failed)) if failed else f"Read in {report.get('seconds', 0):.1f} s"})
    elif sitting.get("events", {}).get("queued"):
      steps.append({"key": "read", "state": "RUNNING", "detail": "The reader is running."})
    else:
      steps.append({"key": "read", "state": "OPEN", "detail": None})
    steps.append(await self._run_step(org, project_id))
    open_rows = 0
    if held and steps[-1]["state"] != "RUNNING":
      open_rows = (await ReviewService(self.session).review(org, project_id))["open"]
      steps.append({"key": "review", "state": "OPEN" if open_rows else "DONE", "detail": f"{open_rows} row(s) still need a decision"})
    else:
      steps.append({"key": "review", "state": "OPEN", "detail": None})
      
    ready = bool(held) and steps[2]["state"] == "DONE"
    steps.append({"key": "boq", "state": "READY" if ready else "OPEN", "detail": None})
    steps.append({"key": "export", "state": "DONE" if sitting.get("exports") else ("READY" if ready else "OPEN"), "detail": f"{len(sitting.get('exports') or [])} export(s)"})
    nxt = next((s["key"] for s in steps if s["state"] in ("OPEN", "RUNNING", "FAILED") and s["key"] != "review"), None)
    uploaded = min((d.created_at for d in drawings), default=None)
    return {"project_id": project_id, "steps": steps, "next": nxt, "open_rows": open_rows, "sitting": SIT.summary(sitting, uploaded, report), "profile": profile.id, "profile_source": source,
      "profiles": [{"id": p.id, "label": p.label} for p in P.all_profiles().values()]}

  async def _flow(self, org: UUID, project_id: UUID, requested: str | None, book_id: UUID | None):
    profile, source = await self._profile(org, requested)
    prepared, head, _profile = await self._prepared(org, project_id, profile.id, book_id)
    if prepared is None:
      return None
    
    body, lines, totals, mats = priced_view(prepared["billed"], prepared["parts"], prepared["parts"]["measured"], profile, prepared["items"], prepared["rows"])
    review = await ReviewService(self.session).review(org, project_id)
    conf = (head.get("source") or {}).get("confidence")
    marks = MK.line_marks(prepared["billed"].lines, lines, review["rows"], conf)
    block = MK.confidence_block(marks, conf)
    body["lines"] = [{**ln, **{k: m[k] for k in ("state", "label", "priced", "measured_amount", "assumed_amount", "low_pct", "high_pct", "elements", "open_rows", "confidence", "confidence_why")}} for ln, m in zip(body["lines"], marks)]
    body.update({"profile_source": source, "banner": MK.banner(body["totals"], review["open"], block["high_pct"]), "open_rows": review["open"], "coverage": MK.coverage(prepared["entries"]), "assumptions": MK.assumptions(prepared["entries"]),
      "confidence": block, "checks": (head.get("source") or {}).get("checks") or []})
    return {"head": head, "body": body, "lines": lines, "totals": totals, "mats": mats, "marks": marks, "profile": profile, "rows": review["rows"], "books": prepared["rows"]}

  async def boq(self, org: UUID, project_id: UUID, requested: str | None = None, book_id: UUID | None = None) -> dict:
    got = await self._flow(org, project_id, requested, book_id)
    if got is None:
      profile, source = await self._profile(org, requested)
      empty = await self.priced(org, project_id, profile.id, book_id)
      return {**empty, "profile_source": source, "banner": [], "open_rows": 0, "coverage": [], "assumptions": [], "confidence": dict(MK.NO_CONFIDENCE), "checks": []}
    return {**got["head"], "has_ledger": True, **got["body"]}

  async def _title(self, org: UUID, project_id: UUID) -> list:
    company = (await self.session.execute(select(Organization.name).where(Organization.id == org))).scalar_one_or_none()
    project = (await self.session.execute(select(Project.name).where(Project.id == project_id))).scalar_one_or_none()
    return [f"Company: {company or '-'}", f"Project: {project or str(project_id)}"]

  async def export(self, org: UUID, project_id: UUID, kind: str, requested: str | None = None, book_id: UUID | None = None) -> tuple:
    if kind not in KINDS:
      raise TraceException(f"'{kind}' is not an export of the flow.", status_code=422, code="EXPORT_UNKNOWN")
    got = await self._flow(org, project_id, requested, book_id)
    if got is None:
      raise TraceException("This project has no ledger yet. Run the first-upload job.", status_code=409, code="NO_LEDGER")
    body, profile = got["body"], got["profile"]
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    books = ", ".join(f"{b['code']} v{b['version']}" for b in got["books"]) or "none"
    meta = [*await self._title(org, project_id), f"Billing profile: {profile.label} ({body['profile_source'].lower()})", f"Rate book: {books}", f"Generated: {now}"]
    
    if kind == "xlsx":
      data = X.build_xlsx(str(project_id), profile.id, got["lines"], got["totals"], got["mats"], None, now, got["marks"])
    elif kind == "priced_pdf":
      data = DOC.priced_pdf("Priced bill of quantities", meta, body["banner"], body["lines"], body["totals"], MK.TEXT["footer"])
    else:
      unpriced = [ln for ln in body["lines"] if ln["amount"] is None][:MK.LIMITS["unpriced_in_report"]]
      open_rows = [r for r in got["rows"] if r["state"] == MK.OPEN]
      data = DOC.client_pdf("Client report", meta, body["banner"], body["totals"], body["coverage"], open_rows, body["assumptions"], unpriced, MK.TEXT["footer"])
    await self.record(org, project_id, SIT.EXPORT, {"kind": kind, "profile": profile.id, "rate_books": [b["code"] for b in got["books"]]})
    media, ext, stem = KINDS[kind]
    return data, media, f"{stem}-{project_id}.{ext}"
