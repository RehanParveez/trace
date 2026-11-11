from __future__ import annotations
import re
from app.engine.catalogue import choices as CH
from app.engine.catalogue import loader as CAT
from app.engine.catalogue import conventions as CV
from app.engine.catalogue import standards as STD
from app.engine.measure import line_sources as LS

KIND_SOURCE = {"STANDARD": "standard", "QS_CONVENTION": "qs", "TRACE_SEED": "seed"}
STATE_SOURCE = {CH.PRINTED: "drawing", CH.DECIDED: "choice", CH.DEFAULT: "qs"}
BAG_KG = 50.0
MORTAR_TABLE = "STD_MORTAR_DRY_MATERIAL"
BRICKS_PER_CFT, MORTAR_PER_100, CEMENT_KG_CFT, DRY_FACTOR = "STD_BRICKS_PER_CFT", "STD_MORTAR_WET_PER_100CFT_BRICK", "STD_CEMENT_KG_PER_CFT", "STD_CONCRETE_DRY_FACTOR"
BINDING_KG_PER_T = "PK_BINDING_WIRE_KG_PER_T"
MM_FT = 304.8
MIX = re.compile(r"^1\s*:\s*(\d+(?:\.\d+)?)\s*:\s*(\d+(?:\.\d+)?)$")
RATIO = re.compile(r"^1\s*:\s*(\d+(?:\.\d+)?)$")
PLASTER_CARD = {"WALL_PLASTER": ("PLASTER_INSIDE", "plaster_inside_mm"), "WALL_PLASTER_EXT": ("PLASTER_OUTSIDE", "plaster_outside_mm"), "CEILING_PLASTER": ("PLASTER_CEILING", "plaster_ceiling_mm")}
SHEET_CARD = {"MS-02": "MORTAR_45"}
WHOLE, PART = "BRICK_WALLS", "RCC_BEAMS_SLABS"

def _families(qty: str) -> set:
  out = set()
  for it in CAT.items():
    for b in it.billing.PRIVATE_QS:
      if b.qty == qty:
        out.add(b.line)
  return out

def constant(entry_id: str) -> dict:
  e = STD.entry(entry_id)
  if e is None:
    c = CV.get(entry_id)
    return {"id": entry_id, "value": c["value"], "source": KIND_SOURCE[c["source"]["kind"]], "kind": c["source"]["kind"], "label": c["source"]["label"]}
  src = STD.source(entry_id)
  return {"id": entry_id, "value": STD.value(entry_id), "source": KIND_SOURCE[src["kind"]], "kind": src["kind"], "label": STD.label(entry_id)}

def _val(c: dict) -> float:
  return float(c["value"])

def choices_for(answers: dict | None, printed: dict | None = None, use_defaults: bool | None = None, base: dict | None = None) -> dict:
  out = {}
  for c in CH.cards():
    got = CH.resolve(c, printed, answers, use_defaults)
    if got["state"] != CH.OPEN:
      out[c["id"]] = {"value": got["value"], "record": got["record"], "spec_values": got["spec_values"], "source": STATE_SOURCE[got["state"]]}
  if (base or {}).get("concrete_mix") and "CONCRETE_NO_MIX" not in out:
    out["CONCRETE_NO_MIX"] = {"value": base["concrete_mix"], "record": {}, "spec_values": {"concrete_mix": base["concrete_mix"]}, "source": "choice"}
  return out

def _table(pins: dict | None = None) -> dict | None:
  rows = STD.table(MORTAR_TABLE, pins)
  if not rows:
    return None
  return {r["ratio"]: [float(x) for x in r["values"][:2]] for r in rows if len(r.get("values") or []) >= 2}

def _mortar_materials(wet_cft: float, ratio: str, table: dict | None) -> tuple:
  if table is None:
    return None, None, "the mortar table of the rate book is not pinned (standards_check pin)"
  row = table.get(ratio)
  if row is None:
    return None, None, f"the mortar table has no row for {ratio}"
  return round(wet_cft * row[0] / 100.0, 3), round(wet_cft * row[1] / 100.0, 3), None

def _table_constant(ratio: str, row: list) -> dict:
  return {**constant(MORTAR_TABLE), "value": f"{ratio}: {row[0]:g} bags of cement and {row[1]:g} cft of sand per 100 cft of wet mortar"}

def _line(material: str, value, unit: str, of: str, inputs: list, constants: list, note: str | None = None) -> dict:
  return {"material": material, "value": None if value is None else round(float(value), 3), "unit": unit, "of": of, "inputs": inputs, "constants": [{k: c[k] for k in ("id", "value", "source", "label")} for c in constants], "note": note}

def schedule(lines: list, chosen: dict | None = None, pins: dict | None = None) -> dict:
  chosen = chosen or {}
  table = _table(pins)
  out, unresolved = [], []
  by = {}
  for ln in lines:
    if ln.get("value") is not None and ln.get("family"):
      by.setdefault(ln["family"], []).append(ln)

  def total(family: str, unit: str) -> tuple:
    rows = [ln for ln in by.get(family, []) if (ln.get("unit") or unit) == unit]
    return sum(float(ln["value"]) for ln in rows), LS.merge([ln.get("inputs") for ln in rows])

  bricks_c, mortar_c, cement_c = constant(BRICKS_PER_CFT), constant(MORTAR_PER_100), constant(CEMENT_KG_CFT)
  for fam in sorted(_families("brick_volume")):
    for ln in by.get(fam, []):
      if (ln.get("unit") or "cft") != "cft":
        continue
      
      v = float(ln["value"])
      card = SHEET_CARD.get(ln.get("item"), "MORTAR_9")
      of = f"{fam} {v:g} cft" + (f" ({ln['item']})" if ln.get("item") else "")
      out.append(_line("bricks", v * _val(bricks_c), "nos", of, ln.get("inputs") or [], [bricks_c]))
      wet = v * _val(mortar_c) / 100.0
      out.append(_line("wet mortar", wet, "cft", of, ln.get("inputs") or [], [mortar_c]))
      got = chosen.get(card)
      ratio = (got or {}).get("record", {}).get("brick_mortar")
      if not ratio:
        unresolved.append({"of": of, "why": f"no mortar ratio: the card {card} is not answered, printed or defaulted"})
        continue
      bags, sand, why = _mortar_materials(wet, ratio, table)
      if why:
        unresolved.append({"of": of, "why": why})
        continue
      src = [{"param": f"{card}", "value": ratio, "source": got["source"]}]
      out.append(_line("cement (mortar)", bags, "bags", of, src, [_table_constant(ratio, table[ratio])]))
      out.append(_line("sand (mortar)", sand, "cft", of, src, [_table_constant(ratio, table[ratio])]))

  for fam, (card, key) in PLASTER_CARD.items():
    for ln in by.get(fam, []):
      if (ln.get("unit") or "sft") != "sft":
        continue
      a = float(ln["value"])
      of = f"{fam} {a:g} sft"
      got = chosen.get(card)
      ratio = (got or {}).get("record", {}).get("plaster_ratio")
      mm = (got or {}).get("record", {}).get(key)
      if not ratio or not mm:
        unresolved.append({"of": of, "why": f"no plaster mix and thickness: the card {card} is not answered, printed or defaulted"})
        continue
      
      wet = a * float(mm) / MM_FT
      src = [{"param": card, "value": f"{ratio} at {mm} mm", "source": got["source"]}]
      out.append(_line("wet plaster mortar", wet, "cft", of, (ln.get("inputs") or []) + src, []))
      bags, sand, why = _mortar_materials(wet, ratio, table)
      if why:
        unresolved.append({"of": of, "why": why})
        continue
      out.append(_line("cement (plaster)", bags, "bags", of, src, [_table_constant(ratio, table[ratio])]))
      out.append(_line("sand (plaster)", sand, "cft", of, src, [_table_constant(ratio, table[ratio])]))

  conc = _families("concrete_volume")
  if PART in conc and any(f in by for f in ("RCC_BEAMS", "RCC_SLABS")):
    conc = conc - {PART}
  wet_total, c_inputs = 0.0, []
  for fam in sorted(conc):
    v, ins = total(fam, "cft")
    wet_total += v
    c_inputs += ins
  if wet_total > 0:
    of = f"concrete {wet_total:g} cft wet (RCC lines)"
    mix = (chosen.get("CONCRETE_NO_MIX") or {})
    m = MIX.match(str(mix.get("value") or "").replace("½", ".5"))
    dry_c, kg_c = constant(DRY_FACTOR), cement_c
    out.append(_line("concrete wet", wet_total, "cft", of, c_inputs, []))
    
    if not m:
      unresolved.append({"of": of, "why": "no nominal mix: the card CONCRETE_NO_MIX is not answered, printed or defaulted" if not mix else f"the mix {mix.get('value')!r} is not a nominal mix (1:a:b); cement and aggregate need a mix design"})
    else:
      a, b = float(m.group(1)), float(m.group(2))
      dry = wet_total * _val(dry_c)
      parts = 1.0 + a + b
      bag_cft = BAG_KG / _val(kg_c)
      src = [{"param": "CONCRETE_NO_MIX", "value": mix["value"], "source": mix["source"]}]
      out.append(_line("cement (concrete)", dry / parts / bag_cft, "bags", of, src, [dry_c, kg_c]))
      out.append(_line("sand (concrete)", dry * a / parts, "cft", of, src, [dry_c]))
      out.append(_line("crush (concrete)", dry * b / parts, "cft", of, src, [dry_c]))

  steel, s_inputs = total("STEEL", "kg")
  if steel > 0:
    bw = constant(BINDING_KG_PER_T)
    of = f"steel {steel:g} kg (as the steel lines give it, wastage in them)"
    out.append(_line("steel", steel, "kg", of, s_inputs, []))
    out.append(_line("binding wire", steel / 1000.0 * _val(bw), "kg", of, [], [bw], "for a material list only: the rate of MRS 6-12 includes the binding wire"))

  totals: dict = {}
  for r in out:
    if r["value"] is None:
      continue
    k = (r["material"].split(" (")[0], r["unit"])
    totals[k] = round(totals.get(k, 0.0) + r["value"], 3)
  return {"lines": out, "totals": {f"{m} ({u})": v for (m, u), v in sorted(totals.items())}, "unresolved": unresolved}

def plain_lines(sched: dict) -> list:
  L = []
  for r in sched["lines"]:
    ins = ", ".join(f"{i['param']}={i['value']} ({i['source']})" for i in r["inputs"]) or "geometry only"
    cons = ", ".join(f"{c['id']}={c['value']} ({c['source']})" for c in r["constants"]) or "none"
    L.append(f"{r['material']}: {r['value']:g} {r['unit']} of {r['of']}; inputs: {ins}; constants: {cons}")
  L += [f"NOT COMPUTED {u['of']}: {u['why']}" for u in sched["unresolved"]]
  return L
