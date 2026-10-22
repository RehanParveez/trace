from __future__ import annotations
from app.modules.drawings_boq.takeoff.reading_score import reading_score as S
from app.modules.drawings_boq.takeoff.tuning import registry as R
from app.modules.drawings_boq.takeoff.tuning.sweep import BASE, COMPLETE, OPEN, PERTURBED

DECISION_VERSION = 1
KEEP, CHANGE, INSUFFICIENT, INERT, REPORT_ONLY, INCOMPLETE = "KEEP", "CHANGE", "INSUFFICIENT", "INERT", "REPORT_ONLY", "INCOMPLETE"

class Policy:
  def __init__(self, min_gain: float = 0.01, min_labels: int = 30, regression_tol: float = 0.02, gate_min_units: int = 5):
    self.min_gain, self.min_labels, self.regression_tol, self.gate_min_units = float(min_gain), int(min_labels), float(regression_tol), int(gate_min_units)

  def as_dict(self) -> dict:
    return {"min_gain": self.min_gain, "min_labels": self.min_labels, "regression_tol": self.regression_tol, "gate_min_units": self.gate_min_units}

  @staticmethod
  def for_sweep(result: dict, **over) -> "Policy":
    rule = next((c["rule"] for c in result.get("cases", []) if c["role"] == BASE), None) or next((c["rule"] for c in result.get("cases", [])), None)
    base = S.MatchRule.from_dict(rule)
    kw = {"regression_tol": base.regression_tol, "gate_min_units": base.gate_min_units}
    kw.update(over)
    return Policy(**kw)

def _rows(pools: dict, role: str, basis: str | None, pred=None) -> list:
  out = []
  for b in ((basis,) if basis else (COMPLETE, OPEN)):
    out += [r for r in (pools.get(f"{role}:{b}") or {}).get("families", []) if pred is None or pred(r["family"])]
  return out

def _sum(rows: list) -> dict:
  tp, fp, fn = (sum(r[k] for r in rows) for k in ("tp", "fp", "fn"))
  return {"labels": sum(r["labels"] for r in rows), "found": sum(r["found"] for r in rows), "tp": tp, "fp": fp, "fn": fn,
    "wrong_confirmed": sum(r["wrong_confirmed"] for r in rows), "unlabelled": sum(r["unlabelled"] for r in rows), "f1": f1_of(tp, fp, fn)}

def f1_of(tp: int, fp: int, fn: int) -> float | None:
  if tp + fp + fn == 0:
    return None
  return S.ratios(tp, fp, fn)["f1"] or 0.0

def _round(v):
  return None if v is None else round(v, 4)

def _fam_view(pools: dict, role: str, basis: str) -> dict:
  return {r["family"]: (r["tp"], r["fp"], r["fn"]) for r in _rows(pools, role, basis)}

def _moved(control: dict, cell: dict) -> list:
  out = set()
  for role in (BASE, PERTURBED):
    for basis in (COMPLETE, OPEN):
      a, b = _fam_view(control["pools"], role, basis), _fam_view(cell["pools"], role, basis)
      out |= {f for f in set(a) | set(b) if a.get(f) != b.get(f)}
  return sorted(out)

def guards(control: dict, cell: dict, p: R.Param | None, pol: Policy, affected) -> list:
  out = []
  c_all, n_all = _sum(_rows(control["pools"], BASE, COMPLETE)), _sum(_rows(cell["pools"], BASE, COMPLETE))
  ok = (n_all["f1"] or 0.0) >= (c_all["f1"] or 0.0) - 1e-9
  out.append({"name": "NO_NET_LOSS", "ok": ok, "detail": f"F1 of all kinds on the complete sheets {_round(c_all['f1'])} -> {_round(n_all['f1'])}"})
  old = {r["family"]: r for r in _rows(control["pools"], BASE, COMPLETE)}
  bad = []
  for r in _rows(cell["pools"], BASE, COMPLETE):
    o = old.get(r["family"])
    if o is None or o["labels"] < pol.gate_min_units:
      continue
  
    a, b = f1_of(o["tp"], o["fp"], o["fn"]), f1_of(r["tp"], r["fp"], r["fn"])
    if a is not None and (b or 0.0) < a - pol.regression_tol:
      bad.append(f"{r['family']} {_round(a)} -> {_round(b)}")
  out.append({"name": "NO_KIND_FALLS", "ok": not bad, "detail": "; ".join(bad) or f"no kind with {pol.gate_min_units} or more labelled members fell by more than {pol.regression_tol:g}"})
  co, no = _sum(_rows(control["pools"], BASE, OPEN)), _sum(_rows(cell["pools"], BASE, OPEN))
  ok = no["tp"] >= co["tp"] and no["wrong_confirmed"] <= co["wrong_confirmed"]
  out.append({"name": "PARTLY_LABELLED_SHEETS_HOLD", "ok": ok, "detail": f"confirmed finds {co['tp']} -> {no['tp']}, finds a person rejected {co['wrong_confirmed']} -> {no['wrong_confirmed']}"})
  cp, np_ = _sum(_rows(control["pools"], PERTURBED, None)), _sum(_rows(cell["pools"], PERTURBED, None))
  if cp["labels"] or cp["found"]:
    ok = (np_["f1"] or 0.0) >= (cp["f1"] or 0.0) - pol.regression_tol - 1e-9
    out.append({"name": "PERTURBED_COPIES_HOLD", "ok": ok, "detail": f"F1 on the perturbed copies {_round(cp['f1'])} -> {_round(np_['f1'])}"})
  return out

def decide_param(res: dict, control: dict, pol: Policy) -> dict:
  p = R.get(res["key"])
  head = {"key": p.key, "rule_id": p.rule_id, "basis": p.basis, "hand": p.hand, "current": res["current"], "proposed": None, "families": list(p.families)}
  aff = lambda fam: R.family_matches(fam, p.families)
  cells = res["values"]
  if any(c["failed"] for c in cells):
    bad = next(c for c in cells if c["failed"])
    return {**head, "action": INCOMPLETE, "reasons": [f"The reader failed on a sheet when the value was {bad['value']:g}, so the runs cannot be compared."], "evidence": {}}
  if res.get("inert"):
    return {**head, "action": INERT, "reasons": ["No value tried changed any score on these sheets. The rule may not fire on them, so they say nothing about it."], "evidence": {}}
  base = _sum(_rows(control["pools"], BASE, COMPLETE, aff))
  if not any(k.startswith(f"{BASE}:{COMPLETE}") for k in control["pools"]) or base["labels"] < pol.min_labels:
    return {**head, "action": INSUFFICIENT, "evidence": {"labels": base["labels"], "needed": pol.min_labels},
      "reasons": [f"The complete sheets hold {base['labels']} labelled member(s) of the kinds this constant is for ({', '.join(p.families) or 'none'}); {pol.min_labels} are needed. "
        "Label more of the sheet completely (every member of it)."]}
    
  c_f1 = base["f1"] if base["f1"] is not None else 0.0
  scored = []
  for cell in cells:
    n = _sum(_rows(cell["pools"], BASE, COMPLETE, aff))
    scored.append({"value": cell["value"], "f1": n["f1"] if n["f1"] is not None else 0.0, "tp": n["tp"], "fp": n["fp"], "fn": n["fn"], "cell": cell})
  ladder = sorted([*scored, {"value": res["current"], "f1": c_f1, "tp": base["tp"], "fp": base["fp"], "fn": base["fn"], "cell": None}], key=lambda x: x["value"])
  qualified, tried = [], []
  
  for i, s in enumerate(ladder):
    if s["cell"] is None:
      continue
    why = []
    gain = s["f1"] - c_f1
    if gain < pol.min_gain - 1e-9:
      why.append(f"gain {gain:+.4f} is under {pol.min_gain:g}")
    gs = guards(control, s["cell"], p, pol, aff)
    why += [f"{g['name']}: {g['detail']}" for g in gs if not g["ok"]]
    near = [ladder[j] for j in (i - 1, i + 1) if 0 <= j < len(ladder)]
    spike = [n["value"] for n in near if n["f1"] < c_f1 - 1e-9]
    
    if spike:
      why.append(f"a spike: the neighbouring value(s) {', '.join(f'{v:g}' for v in spike)} score under the current one")
    tried.append({"value": s["value"], "f1": _round(s["f1"]), "gain": _round(gain), "ok": not why, "why_not": why})
    if not why:
      qualified.append((s, gs, near))
  pooled_ev = {"affected_families": sorted({r["family"] for r in _rows(control["pools"], BASE, COMPLETE, aff)}), "labels": base["labels"],
    "complete_sheets": control["pools"].get(f"{BASE}:{COMPLETE}", {}).get("sheets", 0), "f1_now": _round(c_f1), "tp_fp_fn_now": [base["tp"], base["fp"], base["fn"]], "tried": tried}
  if not qualified:
    best = max(tried, key=lambda t: (t["f1"] or 0.0), default=None)
    return {**head, "action": KEEP if p.calibratable else REPORT_ONLY, "evidence": pooled_ev,
      "reasons": ["No value tried passes every test of the rule." + (f" The best score was at {best['value']:g} ({best['f1']}): {'; '.join(best['why_not']) or 'passes'}." if best else "")]}
    
  qualified.sort(key=lambda q: (-q[0]["f1"], abs(q[0]["value"] - res["current"])))
  s, gs, near = qualified[0]
  moved = _moved(control, s["cell"])
  
  ev = {**pooled_ev, "chosen": {"value": s["value"], "f1": _round(s["f1"]), "gain": _round(s["f1"] - c_f1), "tp_fp_fn": [s["tp"], s["fp"], s["fn"]]},
    "neighbours": [{"value": n["value"], "f1": _round(n["f1"])} for n in near], "guards": gs, "kinds_that_moved": moved,
    "kinds_moved_outside_the_rule": [f for f in moved if not aff(f)]}
  if not p.calibratable:
    return {**head, "action": REPORT_ONLY, "proposed": s["value"], "evidence": ev,
      "reasons": [f"Passes every test at {s['value']:g}, but {p.rule_id} is a {p.basis} rule: a score does not change it. A person decides."]}
  return {**head, "action": CHANGE, "proposed": s["value"], "evidence": ev,
    "reasons": [f"F1 of {', '.join(pooled_ev['affected_families'])} on the complete sheets {_round(c_f1)} -> {_round(s['f1'])} over {base['labels']} labelled members."]}

def decide(result: dict, policy: Policy | None = None) -> dict:
  pol = policy or Policy.for_sweep(result)
  ds = [decide_param(r, result["control"], pol) for r in result["params"]]
  counts: dict = {}
  
  for d in ds:
    counts[d["action"]] = counts.get(d["action"], 0) + 1
  return {"decision_version": DECISION_VERSION, "policy": pol.as_dict(), "decisions": ds, "counts": counts, "skipped": result.get("skipped", []), "partial": bool(result.get("partial")),
    "design": result.get("design"), "joint": None}

def joint_guards(control: dict, joint_eval: dict, changes: list, pol: Policy) -> dict:
  everything = lambda fam: True
  gs = guards(control, {"pools": joint_eval["pools"]}, None, pol, everything)
  return {"changes": changes, "ok": all(g["ok"] for g in gs) and not joint_eval["failed"], "guards": gs, "failed": joint_eval["failed"]}
