from __future__ import annotations

TYPED_KEYS = ("wall_height_mm", "column_height_mm", "footing_depth_mm", "slab_thickness_mm", "beam_depth_mm", "plinth_beam_depth_mm", "tie_band_depth_mm",
  "neck_height_mm", "excavation_depth_mm", "trench_depth_mm", "pcc_thickness_mm", "pcc_strip_width_mm", "tank_wall_height_mm", "stair_waist_mm")
NEVER = ("ERROR", "NOT_MEASURABLE", "FLOOR_SOURCE_UNDECIDED")
DEFAULT_BATCH = 150
MAX_BATCH = 400
MAX_LISTED = 40

def typed_values(raw: dict | None) -> dict:
  return {k: raw[k] for k in TYPED_KEYS if raw and raw.get(k) is not None}

def pick(ready: dict, *, accept_assumed: bool, accept_warned: bool, typed: dict, exclude: set | None = None) -> dict:
  exclude = exclude or set()
  skipped: dict = {}
  ids = [i["id"] for i in ready.get("ready", []) if i["id"] not in exclude]
  decided = 0
  
  for item in ready.get("held", []):
    if item["id"] in exclude:
      continue
    codes = [r["code"] for r in item.get("reasons", [])]
    if "ALREADY_DECIDED" in codes:
      decided += 1
      continue
    blocked = next((c for c in codes if c in NEVER), None)
    
    if blocked is None:
      for c in codes:
        ok = (bool(typed) if c == "VALUE_MISSING" else accept_assumed if c == "ASSUMED" else accept_warned if c in ("WARNING", "CHECK_WARNS") else False)
        if not ok:
          blocked = c
          break
    if blocked is None:
      ids.append(item["id"])
    else:
      skipped[blocked] = skipped.get(blocked, 0) + 1
  return {"ids": ids, "already_decided": decided, "skipped": skipped}

def by_code(failures: list) -> dict:
  out: dict = {}
  for f in failures:
    code = f.get("code") or "FAILED"
    out[code] = out.get(code, 0) + 1
  return out

async def run(steps, *, accept_assumed: bool = False, accept_warned: bool = False, typed: dict | None = None, exclude: set | None = None, batch: int = DEFAULT_BATCH,
  confirm: bool = True, dry_run: bool = False) -> dict:
  typed = typed_values(typed)
  batch = max(1, min(int(batch), MAX_BATCH))
  floors_pending = await steps.floors_pending() if dry_run else 0
  
  floors = [] if dry_run else await steps.choose_floors()
  chosen = pick(await steps.ready(), accept_assumed=accept_assumed, accept_warned=accept_warned, typed=typed, exclude=exclude)
  ids = chosen["ids"]
  take, remaining = ids[:batch], max(0, len(ids) - batch)
  out = {"dry_run": dry_run, "floors_chosen": floors, "floors_pending": floors_pending, "would_accept": len(ids), "accepted": 0, "accept_failed": [], "failed_ids": [],
    "failed_by_code": {}, "confirmed": 0, "confirm_failed": [], "already_decided": chosen["already_decided"], "skipped_by_reason": chosen["skipped"], "remaining": remaining}
  
  if dry_run:
    counts = await steps.counts()
    out.update(confirmed_total=counts["confirmed"], draft_total=counts["draft"], would_confirm=counts["draft"] + len(ids))
    return out
  accepted: list = []
  failed: list = []
  
  if take:
    got = await steps.accept(take, typed)
    accepted, failed = got.get("accepted", []), got.get("failed", [])
  out["accepted"] = len(accepted)
  out["failed_ids"] = [f["id"] for f in failed if f.get("id")]
  out["failed_by_code"] = by_code(failed)
  out["accept_failed"] = failed[:MAX_LISTED]
  
  if confirm:
    drafts = await steps.draft_measurements()
    
    if drafts:
      done = await steps.confirm(drafts)
      out["confirmed"] = len(done.get("confirmed", []))
      out["confirm_failed"] = list(done.get("failed", []))[:MAX_LISTED]
  
  if take or out["confirmed"]:
    await steps.resync()
  counts = await steps.counts()
  out.update(confirmed_total=counts["confirmed"], draft_total=counts["draft"])
  return out
