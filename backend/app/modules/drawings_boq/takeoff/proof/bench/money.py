from __future__ import annotations
from app.modules.drawings_boq import boq_logic as LOGIC
from app.modules.drawings_boq.takeoff.completeness import ledger as LG
from app.modules.drawings_boq.takeoff.proof.bench import offices as OFF

METHOD_RUN = "PRODUCT_METHOD"
THIN_BELOW = 0.5
FIELDS = ["money_pkr", "within_pkr", "money_pct", "confirmed_items", "unpriced_items", "thin", "drawn_money_pkr", "drawn_within_pkr", "assumed_money_pkr", "assumed_within_pkr", "assumed_share_pct"]
THIN = "THIN"

def rate_entry(element: str, rates: dict) -> tuple | None:
  v = (rates.get("per_item_unit") or {}).get(element)
  if v is None:
    return None
  if isinstance(v, dict):
    if v.get("rate") is None:
      return None
    return float(v["rate"]), (LOGIC.normalise_unit(v["unit"]) if v.get("unit") else None)
  return float(v), None

def to_rate_unit(qty: float, unit, rate_unit) -> float | None:
  if rate_unit is None or not unit:
    return qty
  have, want = LOGIC.normalise_unit(str(unit)), LOGIC.normalise_unit(str(rate_unit))
  if have == want:
    return qty
  a, b = LOGIC.UNIT_TABLE.get(have), LOGIC.UNIT_TABLE.get(want)
  if a is None or b is None or a[0] != b[0]:
    return None
  return qty / float(a[1]) * float(b[1])

def money_of_items(items: list, rates: dict) -> dict:
  total, priced, unpriced = 0.0, set(), set()
  by_element: dict = {}
  for it in items:
    element = it["element"]
    entry = rate_entry(element, rates)
    qty = None if entry is None else to_rate_unit(float(it["quantity"]), it.get("unit"), entry[1])
    if qty is None:
      unpriced.add(element)
      continue
    money = qty * entry[0]
    by_element[element] = by_element.get(element, 0.0) + money
    priced.add(element)
    total += money
  return {"money": total, "priced": sorted(priced), "unpriced": sorted(unpriced - priced), "by_element": by_element}

def within_money(rows: list, rates: dict) -> float:
  by: dict = {}
  for r in rows:
    by.setdefault(r["element"], []).append(r)
  total = 0.0
  for element, rs in sorted(by.items()):
    entry = rate_entry(element, rates)
    if entry is None:
      continue
    use = [r for r in rs if r["floor"] == LG.ALL] or rs
    for r in use:
      if r["answer_qty"] in (None, 0) or not r["within_tol"]:
        continue
      qty = to_rate_unit(float(r["answer_qty"]), r.get("unit"), entry[1])
      if qty is not None:
        total += qty * entry[0]
  return total

DRAWN, ASSUMED, NONE = "DRAWN", "ASSUMED", "NONE"

def element_class(rows: list) -> dict:
  """Where the money of each element rests, from the rows' money_source: ASSUMED when any floor row is, DRAWN when none is and one is drawn, else NONE."""
  by: dict = {}
  for r in rows:
    if r.get("money_source"):
      by.setdefault(r["element"], set()).add(r["money_source"])
  return {el: ASSUMED if ASSUMED in cs else DRAWN if DRAWN in cs else NONE for el, cs in by.items()}

def within_by_element(rows: list, rates: dict) -> dict:
  by: dict = {}
  for r in rows:
    by.setdefault(r["element"], []).append(r)
  out: dict = {}
  for element, rs in sorted(by.items()):
    entry = rate_entry(element, rates)
    if entry is None:
      continue
    total = 0.0
    for r in [r for r in rs if r["floor"] == LG.ALL] or rs:
      if r["answer_qty"] in (None, 0) or not r["within_tol"]:
        continue
      qty = to_rate_unit(float(r["answer_qty"]), r.get("unit"), entry[1])
      if qty is not None:
        total += qty * entry[0]
    out[element] = total
  return out

def split_fields(rows: list, mine: dict, rates: dict, money: float, defined: bool) -> dict:
  """The workbook money of the confirmed items split by what Trace's number for each rests on (drawn, assumed, or no number), with the part of each that is within
  tolerance, and the assumed share of all the money."""
  cls, within = element_class(rows), within_by_element(rows, rates)
  b = {DRAWN: [0.0, 0.0], ASSUMED: [0.0, 0.0], NONE: [0.0, 0.0]}
  for el, m in mine["by_element"].items():
    c = cls.get(el, NONE)
    b[c][0] += m
    b[c][1] += min(within.get(el, 0.0), m)
  def r2(x):
    return round(x, 2) if defined else None
  return {"drawn_money_pkr": r2(b[DRAWN][0]), "drawn_within_pkr": r2(b[DRAWN][1]), "assumed_money_pkr": r2(b[ASSUMED][0]), "assumed_within_pkr": r2(b[ASSUMED][1]),
    "unread_money_pkr": r2(b[NONE][0]), "assumed_share_pct": round(100.0 * b[ASSUMED][0] / money, 1) if defined else None}

def _pct(w, m) -> str:
  return "-" if not m else f"{100.0 * w / m:.1f}%"

def source_lines(cases: list, table) -> list:
  L = ["## Money by source", "",
    "The money of the confirmed items is split by what Trace's number for each rests on. Drawn money: every input of its lines is the drawing or a user's own figure. Assumed money: at least one input is a standard, a choice default, "
    "a site fallback, a QS rule or a seed, or the line is ASSUMED or ASKED in the ledger. No number: Trace gives none. First-sight money accuracy on each part is its money within tolerance over its money; the assumed share is assumed money over all money. "
    "A pack that raises accuracy by assuming more shows here as a rising assumed share.", ""]
  body, by_office = [], {}
  for c in cases:
    v = c["money"]["headline"]
    if v is None or not v.get("defined") or v.get("drawn_money_pkr") is None:
      continue
    body.append([c["name"], c["office"], f"{v['drawn_money_pkr']:,.0f}", _pct(v["drawn_within_pkr"], v["drawn_money_pkr"]), f"{v['assumed_money_pkr']:,.0f}", _pct(v["assumed_within_pkr"], v["assumed_money_pkr"]),
      f"{v['unread_money_pkr']:,.0f}", f"{v['assumed_share_pct']:.1f}%"])
    o = by_office.setdefault(c["office"], [0.0] * 5)
    for n, k in enumerate(("drawn_money_pkr", "drawn_within_pkr", "assumed_money_pkr", "assumed_within_pkr", "unread_money_pkr")):
      o[n] += v[k]
  if not body:
    return L + ["No set has a money figure with a source split yet.", ""]
  L += table(["Set", "Office", "Drawn money (PKR)", "Accuracy on drawn money", "Assumed money (PKR)", "Accuracy on assumed money", "No number (PKR)", "Assumed share"], body) + [""]
  total = lambda o: o[0] + o[2] + o[4]
  L += ["Per office, money-weighted:", ""] + table(["Office", "Drawn money (PKR)", "Accuracy on drawn money", "Assumed money (PKR)", "Accuracy on assumed money", "Assumed share"],
    [[k, f"{o[0]:,.0f}", _pct(o[1], o[0]), f"{o[2]:,.0f}", _pct(o[3], o[2]), _pct(o[2], total(o))] for k, o in sorted(by_office.items())]) + [""]
  return L

def of_set(rows: list, answers_doc: dict | None, rates: dict) -> dict:
  items = list((answers_doc or {}).get("items") or [])
  confirmed = [it for it in items if it.get("confirmed")]
  mine = money_of_items(confirmed, rates)
  book = money_of_items(items, rates)
  money = mine["money"]
  within = min(within_money(rows, rates), money)
  defined = money > 0
  share = None if not book["money"] else round(100.0 * money / book["money"], 1)
  return {"defined": defined, "money_pkr": round(money, 2) if defined else None, "within_pkr": round(within, 2) if defined else None,
    "money_pct": round(100.0 * within / money, 1) if defined else None, "confirmed_items": len(confirmed), "workbook_items": len(items),
    "unpriced_items": len(mine["unpriced"]), "unpriced": mine["unpriced"], "workbook_pkr": round(book["money"], 2), "confirmed_share_pct": share,
    "thin": bool(defined and book["money"] and money < THIN_BELOW * book["money"]), **split_fields(rows, mine, rates, money, defined)}

def history_fields(view: dict) -> list:
  return ["" if view["money_pkr"] is None else f"{view['money_pkr']:.2f}", "" if view["within_pkr"] is None else f"{view['within_pkr']:.2f}",
    "" if view["money_pct"] is None else f"{view['money_pct']:.1f}", view["confirmed_items"], view["unpriced_items"], THIN if view["thin"] else "",
    *["" if view.get(k) is None else f"{view[k]:.2f}" if k != "assumed_share_pct" else f"{view[k]:.1f}" for k in FIELDS[6:]]]

def _num(v) -> float | None:
  try:
    return None if v in (None, "") else float(v)
  except (TypeError, ValueError):
    return None

def first_money(name: str, history: list) -> dict | None:
  mine = [r for r in history if r.get("set") == name and r.get("run") in (OFF.FIRST_RUN, METHOD_RUN)]
  if not mine:
    return None
  for batch in list(dict.fromkeys(r.get("rows_sha") for r in mine)):
    same = [r for r in mine if r.get("rows_sha") == batch]
    pick = next((r for r in same if r["run"] == METHOD_RUN), same[0])
    money, within = _num(pick.get("money_pkr")), _num(pick.get("within_pkr"))
    if money and within is not None:
      return {"run": pick["run"], "date": str(pick.get("date") or ""), "commit": str(pick.get("commit") or ""), "money_pkr": money, "within_pkr": within, "money_pct": round(100.0 * within / money, 1),
        "confirmed_items": pick.get("confirmed_items"), "thin": pick.get("thin") == THIN}
  return None

def office_table(cases: list) -> list:
  by: dict = {}
  for c in cases:
    v = c["money"]["headline"]
    if v is None or not v["defined"]:
      continue
    o = by.setdefault(c["office"], {"sets": [], "money": 0.0, "within": 0.0, "thin": []})
    o["sets"].append(c["name"])
    o["money"] += v["money_pkr"]
    o["within"] += v["within_pkr"]
    if v["thin"]:
      o["thin"].append(c["name"])
  return [{"office": k, "sets": v["sets"], "money_pkr": round(v["money"], 2), "within_pkr": round(v["within"], 2), "money_pct": round(100.0 * v["within"] / v["money"], 1), "thin": v["thin"]} for k, v in sorted(by.items())]

def lines_for(cases: list, rates: dict, fmt, table) -> list:
  L = ["## First-sight money accuracy", ""]
  L += ["Money is the quantity the QS's workbook gives for each confirmed item times that item's rate in `rates.yaml` (the MRS rate book). Money within tolerance is the same over the items whose Trace number is within the item's own tolerance (`tolerances.yaml`). "
    "The number is their ratio on the product run under the QS's method profile (the product-plus-method run where the set has company rules, the product run where it has none). Only confirmed items count. An item with no rate is counted, never priced or guessed. "
    "A set is marked THIN when its confirmed money is under half of the money of every item the workbook maps.", ""]
  if not (rates.get("per_item_unit") or {}):
    L += ["`bench/rates.yaml` holds no rate, so money is not defined for any set. Run `bench.rates` against the newest Bahawalpur MRS book (TQ-1 step 2).", ""]
    
  body = []
  for c in cases:
    m = c["money"]
    v, p = m["headline"], m["proof"]
    if v is None:
      body.append([c["name"], c["office"], "-", "no answer file", "-", "-", "-", "-", "-", ""])
      continue
    body.append([c["name"], c["office"], m["run"], f"{v['confirmed_items']} of {v['workbook_items']}", "-" if not v["defined"] else f"{v['money_pkr']:,.0f}", "-" if not v["defined"] else f"{v['within_pkr']:,.0f}",
      "-" if v["money_pct"] is None else f"{v['money_pct']:.1f}%", "-" if p is None or p["money_pct"] is None else f"{p['money_pct']:.1f}%", f"{v['unpriced_items']}" + (f" ({', '.join(v['unpriced'][:6])})" if v["unpriced"] else ""),
      "-" if v["confirmed_share_pct"] is None else f"{v['confirmed_share_pct']:.0f}%" + (" THIN" if v["thin"] else "")])
  L += table(["Set", "Office", "Run", "Confirmed answer items of all answer items", "Money (PKR)", "Within tolerance (PKR)", "First-sight money accuracy", "Proof run, for comparison", "Catalogue items with no rate", "Confirmed money of workbook money"], body) + [""]
  offices = office_table(cases)
  
  if offices:
    L += ["Per office, money-weighted over its sets with a defined number:", ""]
    L += table(["Office", "Sets", "Money (PKR)", "Within tolerance (PKR)", "First-sight money accuracy", "THIN sets"],
      [[o["office"], ", ".join(o["sets"]), f"{o['money_pkr']:,.0f}", f"{o['within_pkr']:,.0f}", f"{o['money_pct']:.1f}%", ", ".join(o["thin"]) or "-"] for o in offices]) + [""]
  L += source_lines(cases, table)
  return L

def first_sight_lines(history: list, sets_doc: dict, offices_doc: dict) -> list:
  out = []
  for name in sorted(n for n in offices_doc.get("set_log", {}) if n in (sets_doc.get("sets") or {})):
    got = first_money(name, history)
    first = OFF.first_score(name, history)
    if first is None:
      out.append(f"{name}: not scored yet; the first score is recorded before any truth is written")
    elif got is None:
      out.append(f"{name}: scored {first['date']} (commit {first['commit']}) but no history line has money yet: it needs the QS's confirmed mapping and rates; run the bench again after he confirms, before any pack is applied")
    else:
      out.append(f"{name}: first money line {got['date']} (commit {got['commit']}, {got['run']}), money accuracy {got['money_pct']:.1f}% of {got['money_pkr']:,.0f}" + (", THIN" if got["thin"] else "") + f"; first score line {first['date']} (commit {first['commit']})")
  return out
