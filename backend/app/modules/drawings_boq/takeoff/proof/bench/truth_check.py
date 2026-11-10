from __future__ import annotations
import os
from app.engine.catalogue import loader as CL
from app.engine.catalogue import tolerances as TOL
from app.modules.drawings_boq.takeoff.proof import case_io as CIO
from app.modules.drawings_boq.takeoff.proof.answers import answers as AN
from app.modules.drawings_boq.takeoff.proof.answers import sitting2 as S2
from app.modules.drawings_boq.takeoff.proof.answers import tolerance_sheet as TS
from app.modules.drawings_boq.takeoff.proof.bench import money as MN
from app.modules.drawings_boq.takeoff.proof.bench import offices as OFF
from app.modules.drawings_boq.takeoff.proof.bench import rates as RT
from app.modules.drawings_boq.takeoff.proof.bench import sets as ST

def rate_problems(doc: dict | None = None) -> list:
  doc = AN.read_yaml(RT.RATES) if doc is None else doc
  doc = doc or {}
  priced = doc.get("per_item_unit") or {}
  if not isinstance(priced, dict):
    return ["rates.yaml: per_item_unit must be a mapping"]
  if not priced:
    return []

  out = []
  ids = {i.id for i in CL.items()}
  if not doc.get("book"):
    out.append("rates.yaml: a rate needs the book it comes from (`book`)")
  for k, v in sorted(priced.items()):
    if k not in ids:
      out.append(f"rates.yaml: {k} is not a catalogue item")
    elif not (isinstance(v, dict) and isinstance(v.get("rate"), (int, float)) and v["rate"] > 0 and v.get("unit") and v.get("mrs")):
      out.append(f"rates.yaml: {k} needs a unit, a rate above 0 and the MRS item it comes from")
      
  none = set(doc.get("no_rate") or [])
  both = sorted(none & set(priced))
  if both:
    out.append(f"rates.yaml: {', '.join(both[:5])} is both priced and listed in no_rate")
  loose = sorted(i for i in RT.with_code() if i not in priced and i not in none)
  if loose:
    out.append(f"rates.yaml: {len(loose)} item(s) with an MRS code are neither priced nor in no_rate ({', '.join(loose[:5])}); run bench.rates again")
  return out

def share_problems(doc: dict | None = None) -> list:
  doc = RT.shares_doc() if doc is None else doc
  shares = doc.get("shares") or {}
  if not shares:
    return []

  out = []
  ids = {i.id for i in CL.items()}
  if not (doc.get("confirmed_by") and doc.get("confirmed_date") and doc.get("house")):
    out.append("money_shares.yaml: shares need house, confirmed_by and confirmed_date")
  if len(shares) > RT.TOP:
    out.append(f"money_shares.yaml: {len(shares)} shares; at most {RT.TOP}")
  for k, v in sorted(shares.items()):
    if k not in ids:
      out.append(f"money_shares.yaml: {k} is not a catalogue item")
    if not TOL._pct_ok(v):
      out.append(f"money_shares.yaml: {k} must be above 0 and at most {TOL.MAX_PCT:g}")
  return out

def difference_problems() -> list:
  out = []
  for name in sorted(ST.load()["sets"]):
    path = os.path.join(CIO.HERE, name, S2.FILE)
    if os.path.isfile(path):
      out += S2.problems_of(AN.read_yaml(path), name)
  return out

def first_money_problems() -> list:
  history = OFF.history_rows()
  sets = ST.load()["sets"]
  out = []
  
  for name in sorted(n for n in OFF.load().get("set_log", {}) if n in sets):
    doc = AN.load(os.path.join(CIO.HERE, name))
    if not any(it.get("confirmed") for it in (doc or {}).get("items") or []):
      continue
    if OFF.first_score(name, history) is None:
      out.append(f"{name}: entered as first sight and its mapping is confirmed, but the benchmark has not scored it; run the bench before anything else")
    elif MN.first_money(name, history) is None:
      out.append(f"{name}: entered as first sight and its mapping is confirmed, but no history line holds its money; run the bench (with rates.yaml filled) before any pack is applied, and commit that line with the confirmations")
  return out

def problems() -> list:
  return TOL.problems() + TS.suggestion_problems() + rate_problems() + share_problems() + difference_problems() + first_money_problems()

def gate() -> tuple:
  bad = problems()
  rates = AN.read_yaml(RT.RATES) or {}
  tol = TOL._load()
  note = (f"{len(rates.get('per_item_unit') or {})} rate(s), {len(tol.get('per_item') or {})} tolerance(s)" + (f" confirmed by {tol['confirmed_by']}" if tol.get("confirmed_by") else "")
    + f", {len(RT.shares_doc().get('shares') or {})} money share(s)")
  return not bad, note if not bad else f"{len(bad)} QS truth problem(s)", bad
