from __future__ import annotations

SOURCE = "OUTLINE"
SETTLE_TOL = 0.02      
VETO_TOL = 0.10        
TRUST_CONFIRMED = 0.85
CONFIRM_BASIS = {"DIMENSIONS_WEAK": "DIMENSIONS_AND_OUTLINE", "DECLARED_ONLY": "DECLARED_AND_OUTLINE"}

def _labels(witnesses: list | None, strong: bool) -> dict | None:
  for w in witnesses or []:
    if w.get("source") != "ROOM_LABELS" or not w.get("ratio"):
      continue
    if strong and w.get("strong"):
      return w
    if not strong and not w.get("strong") and int(w.get("support") or 0) >= 2:
      return w
  return None

def _settle(verdict: dict, notes: list, w: float, refs: int, witnesses: list | None, measured: dict | None) -> tuple:
  clusters = (measured or {}).get("clusters") or []
  dims = clusters[0] if clusters else None
  labels = _labels(witnesses, True)
  picks = []
  
  if dims and dims.get("ratio") and abs(w / float(dims["ratio"]) - 1.0) <= SETTLE_TOL:
    picks.append(("DIMENSIONS", float(dims["ratio"]), int(dims.get("support") or 0), None, "DIMENSIONS_AND_OUTLINE"))
  if labels and abs(w / float(labels["ratio"]) - 1.0) <= SETTLE_TOL:
    picks.append(("LABELS", float(labels["ratio"]), int(labels.get("support") or 0), labels.get("check"), "PANELS_AND_OUTLINE" if labels.get("panels") else "ROOMS_AND_OUTLINE"))
  if len(picks) != 1:
    return verdict, notes
  _, ratio, support, check, basis = picks[0]
  text = format(round(ratio, 4), "f").rstrip("0").rstrip(".")
  rec = verdict.get("recommended") or {}
  if picks[0][0] == "DIMENSIONS" and rec.get("basis") == "MEASURED_FROM_DIMENSIONS":
    check = rec.get("check")
  out = dict(verdict)
  out["agreement"] = "VERIFIED_WEAK"
  
  out["recommended"] = {"method": "SCALE_RATIO", "ratio": round(ratio, 4), "scale_text": f"1:{text}", "basis": basis, "trust": TRUST_CONFIRMED, "check": check, "support": support,
    "outline": {"plans": refs}}
  kept = [n for n in notes if n.get("code") != "SCALE_WITNESS_CONFLICT"]
  kept.append({"code": "SCALE_SETTLED_BY_OUTLINE", "message": (
    f"The printed dimensions and the size labels of this sheet gave different scales. The outer walls of the plan are the size of the outer walls of {refs} other plan{'s' if refs != 1 else ''} "
    f"of the set at about 1:{w:.1f}, which is the {'printed dimensions' if picks[0][0] == 'DIMENSIONS' else 'size labels'} (1:{ratio:.1f}), so that scale is used. Check one known length before measuring.")})
  return out, kept

def _rec(ratio: float, k: float | None, refs: int) -> dict:
  text = format(round(ratio, 4), "f").rstrip("0").rstrip(".")
  return {"method": "SCALE_RATIO", "ratio": round(ratio, 4), "scale_text": f"1:{text}", "basis": "MEASURED_FROM_OUTLINE", "trust": 0.8, "check": None, "support": 0,
    "outline": {"k": None if k is None else round(k, 4), "plans": refs}}

def apply(verdict: dict, notes: list, prop: dict | None, declared: dict, agree_tol: float, witnesses: list | None = None, measured: dict | None = None) -> tuple:
  if not prop or prop.get("status") != "PROPOSED" or not prop.get("ratio"):
    return verdict, notes
  w = float(prop["ratio"])
  agreement, rec = verdict.get("agreement"), verdict.get("recommended")
  refs = len(prop.get("refs") or [])
  
  if rec is None and agreement == "NONE":
    if declared.get("not_to_scale"):
      return verdict, notes
    weak = _labels(witnesses, False)
    if weak is not None and abs(w / float(weak["ratio"]) - 1.0) > VETO_TOL:
      return verdict, [*notes, {"code": "SCALE_OUTLINE_VETOED", "message": (
        f"The outer walls of this plan would give about 1:{w:.1f}, but the {int(weak['support'])} size labels written on it that agree give about 1:{float(weak['ratio']):.1f}. "
        "Neither is used. Set the scale on the Measure page from a length you know.")}]
      
    out = dict(verdict)
    out["agreement"] = "OUTLINE_ONLY"
    out["recommended"] = _rec(w, prop.get("k"), refs)
    notes = [n for n in notes if n.get("code") != "NO_SCALE_FOUND"]
    agree = weak is not None
    if agree:
      out["recommended"]["trust"] = TRUST_CONFIRMED
    notes.append({"code": "SCALE_FROM_OUTLINE", "message": (
      f"No scale or dimension is printed on this sheet. The scale (about 1:{w:.1f}) is the one that makes its outer walls the size of the outer walls of "
      f"{refs} other plan{'s' if refs != 1 else ''} of the set" + (f"; the {int(weak['support'])} size labels written on the plan agree with it" if agree else "") + ". Check one known length before measuring.")})
    return out, notes

  if agreement == "WITNESS_CONFLICT" and rec is not None:
    return _settle(verdict, notes, w, refs, witnesses, measured)
  if rec is not None and agreement in CONFIRM_BASIS and not (agreement == "DECLARED_ONLY" and declared.get("not_to_scale")) and abs(w / float(rec["ratio"]) - 1.0) <= SETTLE_TOL:
    out = dict(verdict)
    out["agreement"] = "VERIFIED_WEAK"
    out["recommended"] = {**rec, "trust": max(float(rec.get("trust") or 0.0), TRUST_CONFIRMED), "basis": CONFIRM_BASIS[agreement], "outline": {"plans": refs}}
    return out, [*notes, {"code": "SCALE_CONFIRMED_BY_OUTLINE", "message": (
      f"The scale found on this sheet (about 1:{float(rec['ratio']):.1f}) is confirmed by the outer walls of the plan, which are the size of the outer walls of "
      f"{refs} other plan{'s' if refs != 1 else ''} of the set at this scale.")}]
  if rec is not None and agreement not in ("VERIFIED", "ROOMS_ONLY", "OUTLINE_ONLY"):
    gap = abs(w / float(rec["ratio"]) - 1.0)
    if gap > agree_tol:
      notes = [*notes, {"code": "SCALE_OUTLINE_DIFFERS", "message": (
        f"The outer walls of this plan are the size of the other plans of the set at about 1:{w:.1f}, not at the scale found on this sheet (about 1:{float(rec['ratio']):.1f}). "
        "This is a hint only; check one known length before measuring.")}]
  return verdict, notes

KEEP = ("agreement", "recommended", "notes")

def original(full: dict) -> dict:
  saved = (full.get("outline") or {}).get("original")
  src = saved if saved else full
  return {"agreement": src.get("agreement"), "recommended": src.get("recommended"), "notes": list(src.get("notes") or []), "declared": full.get("declared") or {},
    "measured": full.get("measured"), "witnesses": full.get("witnesses") or []}

def summary(prop: dict | None, refs: list) -> dict | None:
  if not prop:
    return None
  return {"status": prop["status"], "k": None if prop.get("k") is None else round(float(prop["k"]), 4), "ratio": None if not prop.get("ratio") else round(float(prop["ratio"]), 4),
    "refs": refs, "rank": prop.get("rank"), "same_floor": bool(prop.get("same_floor")) or prop.get("rank") == 0, "note": prop.get("note")}

def rebuild(full: dict, prop: dict | None, refs: list, agree_tol: float) -> dict:
  base = original(full)
  verdict, notes = apply({"agreement": base["agreement"], "recommended": base["recommended"]}, base["notes"], prop, base["declared"], agree_tol, base["witnesses"], base["measured"])
  out = {k: v for k, v in full.items() if k != "outline"}
  out["agreement"], out["recommended"], out["notes"] = verdict["agreement"], verdict["recommended"], notes
  changed = verdict["agreement"] != base["agreement"] or verdict["recommended"] != base["recommended"] or notes != base["notes"]
  settled = str((verdict.get("recommended") or {}).get("basis") or "").endswith("_AND_OUTLINE") and verdict["agreement"] != base["agreement"]
  block = {"verdict": {**summary(prop, refs), "applied": verdict.get("agreement") == "OUTLINE_ONLY", "settled": settled}} if prop else {}
  
  if changed:
    block["original"] = {k: base[k] for k in KEEP}
  if block:
    out["outline"] = block
  return out
