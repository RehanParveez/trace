from __future__ import annotations

SOURCE = "OUTLINE"

def _rec(ratio: float, k: float | None, refs: int) -> dict:
  text = format(round(ratio, 4), "f").rstrip("0").rstrip(".")
  return {"method": "SCALE_RATIO", "ratio": round(ratio, 4), "scale_text": f"1:{text}", "basis": "MEASURED_FROM_OUTLINE", "trust": 0.8, "check": None, "support": 0,
    "outline": {"k": None if k is None else round(k, 4), "plans": refs}}

def apply(verdict: dict, notes: list, prop: dict | None, declared: dict, agree_tol: float) -> tuple:
  if not prop or prop.get("status") != "PROPOSED" or not prop.get("ratio"):
    return verdict, notes
  w = float(prop["ratio"])
  agreement, rec = verdict.get("agreement"), verdict.get("recommended")
  refs = len(prop.get("refs") or [])
  
  if rec is None and agreement == "NONE":
    if declared.get("not_to_scale"):
      return verdict, notes
    out = dict(verdict)
    out["agreement"] = "OUTLINE_ONLY"
    out["recommended"] = _rec(w, prop.get("k"), refs)
    notes = [n for n in notes if n.get("code") != "NO_SCALE_FOUND"]
    notes.append({"code": "SCALE_FROM_OUTLINE", "message": (
      f"No scale or dimension is printed on this sheet. The scale (about 1:{w:.1f}) is the one that makes its outer walls the size of the outer walls of "
      f"{refs} other plan{'s' if refs != 1 else ''} of the set. Check one known length before measuring.")})
    
    return out, notes
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
  verdict, notes = apply({"agreement": base["agreement"], "recommended": base["recommended"]}, base["notes"], prop, base["declared"], agree_tol)
  out = {k: v for k, v in full.items() if k != "outline"}
  out["agreement"], out["recommended"], out["notes"] = verdict["agreement"], verdict["recommended"], notes
  changed = verdict["agreement"] != base["agreement"] or verdict["recommended"] != base["recommended"] or notes != base["notes"]
  block = {"verdict": {**summary(prop, refs), "applied": verdict.get("agreement") == "OUTLINE_ONLY"}} if prop else {}
  
  if changed:
    block["original"] = {k: base[k] for k in KEEP}
  if block:
    out["outline"] = block
  return out
