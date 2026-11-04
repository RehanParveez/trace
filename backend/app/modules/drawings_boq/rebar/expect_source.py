"""Builds the inputs of every drawing member for rebar_expect, from what the reading pipeline stored per sheet and from the project's decisions."""
from __future__ import annotations
import re
from app.engine.measure import rebar_expect as RX
from decimal import Decimal as D
from app.modules.drawings_boq.rebar.member_source import candidate_dict, norm_mark, sheet_floor

BARS = re.compile(r"(\d+)\s*-\s*#(\d+)\s*(Thr|Ext)", re.I)
STIRRUP = re.compile(r"#(\d+)\s*@\s*(\d+(?:\.\d+)?)\"?(?:\s*/\s*(\d+(?:\.\d+)?)\")?")
TITLE_SIZE = re.compile(r"(\d+)'-(\d+)\"?\s*x\s*(\d+)'-(\d+)\"?\s*x\s*(\d+)'-(\d+)", re.I)
SPAN_MM = re.compile(r"span\s+(\d+(?:\.\d+)?)\s*mm", re.I)
TANK_WORDS = ("UGWT", "OHWT", "SEPTIC", "HARVESTING")
DEFAULTS = {"stock_length_ft": 40, "bar_count_plus_one": False, "tie_zones": "ZONES", "strip_junction": "ONCE", "round_whole_bars": True, "hook_tie_d": 6, "hook_bar_d": 12}
MEMBER_PLAN = {"COLUMN": RX.column, "BEAM": RX.beam, "PLINTH": RX.plinth_beam, "SLAB": RX.slab_panel, "LINTEL": RX.lintel, "TANK": RX.tank}

def _where(meta: dict, page: int, what: str) -> str:
  no = (meta.get("identity") or {}).get("sheet_no")
  return f"{no} p.{page} {what}" if no else f"p.{page} {what}"

def rules_inputs(sheets: list) -> list:
  out: dict = {}
  for sh in sheets:
    meta = sh.get("meta") or {}
    for f in (meta.get("rebar_rules") or {}).get("facts") or []:
      if f.get("key") and f.get("value") is not None and f["key"] not in out:
        out[f["key"]] = RX.printed(f["key"], f["value"], _where(meta, sh["page_no"], "general notes"))
  return list(out.values())

def decision_inputs(decisions: dict, rules: dict) -> list:
  def pick(key, default, unsure=False):
    if key in decisions and decisions[key] is not None:
      return RX.defaulted(key, decisions[key], f"decision {key}", None)
    flag = "UNSURE,VALUE_DEFAULTED" if unsure else "VALUE_DEFAULTED"
    return RX.defaulted(key, default, f"no decision {key}; assumed", flag)
  out = [pick("stock_length_ft", DEFAULTS["stock_length_ft"], True), pick("bar_count_plus_one", DEFAULTS["bar_count_plus_one"]), pick("tie_zones", DEFAULTS["tie_zones"]),
    pick("strip_junction", DEFAULTS["strip_junction"]), pick("round_whole_bars", DEFAULTS["round_whole_bars"])]
  hooks = decisions.get("hook_lengths") or {}
  
  out.append(RX.defaulted("hook_tie_d", hooks["tie_d"], "decision hook_lengths", None) if "tie_d" in hooks else RX.defaulted("hook_tie_d", DEFAULTS["hook_tie_d"], "no decision hook_lengths; assumed (135 degree tie hook)"))
  out.append(RX.defaulted("hook_bar_d", hooks["bar_d"], "decision hook_lengths", None) if "bar_d" in hooks else RX.defaulted("hook_bar_d", DEFAULTS["hook_bar_d"], "no decision hook_lengths; assumed (90 degree hook)"))
  if decisions.get("link_cut_basis") is not None:
    out.append(RX.defaulted("link_cut_basis", decisions["link_cut_basis"], "decision link_cut_basis", None))
  if decisions.get("column_l0") is not None:
    out.append(RX.defaulted("column_l0_in", decisions["column_l0"], "decision column_l0", None))
  if "curtail_extras" in decisions and decisions["curtail_extras"] is not None:
    out.append(RX.defaulted("curtail_extras", decisions["curtail_extras"], "decision curtail_extras", None))
  elif "CURTAILMENT_TOP" in rules or "CURTAILMENT_BOTTOM" in rules:
    out.append(RX.derived("curtail_extras", True, "the general notes print a curtailment rule"))
  else:
    out.append(RX.defaulted("curtail_extras", False, "no curtailment rule printed and no decision"))
  return out

def _tank_size(sheet_titles: list, word: str) -> list:
  for t in sheet_titles:
    if word in t.upper():
      m = TITLE_SIZE.search(t)
      if m:
        a = [int(x) for x in m.groups()]
        src = "BBS sheet title (not from the drawings)"
        return [RX.defaulted("tank_len_ft", D(a[0]) + D(a[1]) / 12, src, "FROM_BBS_TITLE"), RX.defaulted("tank_wid_ft", D(a[2]) + D(a[3]) / 12, src, "FROM_BBS_TITLE"),
          RX.defaulted("tank_ht_ft", D(a[4]) + D(a[5]) / 12, src, "FROM_BBS_TITLE")]
        
  return []

def _bars(prefix: str, texts: list, src: str) -> RX.Input:
  found = [(int(n), int(b), "Ext" if k.lower() == "ext" else "Thr") for t in texts for n, b, k in BARS.findall(t)]
  return RX.printed(f"{prefix}_bars", found, src)

def _stirrup(spec: str | None, src: str) -> list:
  m = STIRRUP.search(spec or "")
  if not m:
    return []
  bar, end, mid = int(m.group(1)), D(m.group(2)), D(m.group(3) or m.group(2))
  return [RX.printed("stirrup_bar", bar, src), RX.printed("stirrup_end_in", end, src), RX.printed("stirrup_mid_in", mid, src)]

def _override(inputs: list, fields: dict | None, key: str) -> list:
  if not fields:
    return inputs
  by = {i.name: i for i in inputs}
  for f, v in fields.items():
    by[f] = RX.defaulted(f, D(str(v)) if isinstance(v, (int, float)) else v, f"decision member_inputs {key}", None)
  return list(by.values())

def _find_override(table: dict, cls: str, mark: str, floor: str | None):
  want = norm_mark(mark)
  best = None
  for key, fields in table.items():
    parts = key.split(":")
    if parts[0] != cls or norm_mark(parts[1]) != want:
      continue
    
    if len(parts) == 3:
      if floor and parts[2] == floor:
        return key, fields
    elif best is None:
      best = (key, fields)
  return best or (None, None)

def build_jobs(sheets: list, candidates: dict, decisions: dict, bbs_titles: list) -> list:
  rules = rules_inputs(sheets)
  rule_names = {r.name for r in rules}
  base = rules + decision_inputs(decisions, rule_names)
  heights = decisions.get("floor_heights_ft") or {}
  table = decisions.get("member_inputs") or {}
  jobs: list = []
  seen: set = set()

  def add(cls, mark, floor, fn, inputs, plan_count=None, page=None):
    key, fields = _find_override(table, cls, mark, floor)
    if key:
      seen.add(key)
    jobs.append({"cls": cls, "mark": mark, "floor": floor, "fn": fn, "inputs": _override(base + inputs, fields, key or ""), "plan_count": plan_count, "page": page})

  for sh in sheets:
    meta, page = sh.get("meta") or {}, sh["page_no"]
    floor0 = sheet_floor(meta)
    tables = meta.get("structure_tables") or {}
    for c in (tables.get("column_schedule") or {}).get("cells") or []:
      if c.get("state") != "READ" or not c.get("mark"):
        continue
      
      src = _where(meta, page, f"column schedule {c['mark']} {c.get('floor')}")
      steel, size = c.get("steel") or [None, None], (c.get("size") or {}).get("size_in") or [None, None]
      mid, fl = c.get("mid") or {}, c.get("floor")
      ins = [i for i in (RX.printed("size_w_in", D(str(size[0])), src) if size[0] else None, RX.printed("size_d_in", D(str(size[1])), src) if size[1] else None,
        RX.printed("steel_n", steel[0], src) if steel[0] else None, RX.printed("steel_bar", steel[1], src) if steel[1] else None,
        RX.printed("tie_bar", mid.get("bar_no"), src) if mid.get("bar_no") else None, RX.printed("tie_end_in", D(str(mid["end"])), src) if mid.get("end") else None,
        RX.printed("tie_mid_in", D(str(mid["mid"])), src) if mid.get("mid") else None) if i is not None]
      if fl in heights:
        ins.append(RX.defaulted("height_ft", D(str(heights[fl])), "decision floor_heights_ft", None))
      add("COLUMN", str(c["mark"]), fl, RX.column, ins, page=page)
    for s in (tables.get("beam_sections") or {}).get("sections") or []:
      if not s.get("mark"):
        continue
      
      src = _where(meta, page, f"beam section {s['mark']}")
      ins = [RX.printed("width_in", D(str(s["width_in"])), src), RX.printed("depth_in", D(str(s["depth_in"])), src), _bars("top", s.get("top_bars") or [], src),
        _bars("bottom", s.get("bottom_bars") or [], src)] + _stirrup(s.get("stirrup"), src)
      count = next((int(x.get("count") or 1) for r in candidates.get((sh["pdf_key"], page), []) for x in [candidate_dict(r)] if x["category"] == "BEAM" and norm_mark(x.get("tag")) == norm_mark(s["mark"])), None)
      add("BEAM", str(s["mark"]), floor0, RX.beam, [i for i in ins if i.value not in (None, "")], count, page)
    for raw in candidates.get((sh["pdf_key"], page), []):
      c = candidate_dict(raw)
      if c.get("decision") == "REJECTED" or (c.get("facts") or {}).get("set_aside"):
        continue
      
      cat, tag, params = c["category"], c.get("tag"), c["params"] or {}
      if cat == "FOOTING" and tag:
        src = _where(meta, page, f"footing {tag}")
        ins = [RX.printed("depth_in", D(str(params["depth_mm"])) / D("25.4"), src)] if params.get("depth_mm") else []
        add("FOOTING", str(tag), None, RX.strip_footing, ins, int(c.get("count") or 1), page)
      elif cat == "LINTEL" and tag:
        m = SPAN_MM.search(c.get("label") or "")
        ins = [RX.derived("opening_ft", D(m.group(1)) / D("304.8"), _where(meta, page, f"lintel {tag}") + " (drawn span)")] if m else []
        add("LINTEL", str(tag), floor0, RX.lintel, ins, int(c.get("count") or 1), page)
      elif cat == "SITE" and tag and str(tag).upper() in TANK_WORDS:
        add("TANK", str(tag).upper(), None, RX.tank, _tank_size(bbs_titles, str(tag).upper()), 1, page)
  
  for key, fields in table.items():
    if key in seen:
      continue
    parts = key.split(":")
    cls, mark, floor = parts[0], parts[1], parts[2] if len(parts) == 3 else None
    if cls == "FOOTING":
      fn = RX.strip_footing if "strip_length_ft" in fields else RX.pad_footing
    else:
      fn = MEMBER_PLAN[cls]
    tank = _tank_size(bbs_titles, mark.upper()) if cls == "TANK" else []
    jobs.append({"cls": cls, "mark": mark, "floor": floor, "fn": fn, "inputs": _override(base + tank, fields, key), "plan_count": fields.get("plan_count"), "page": None, "decision_only": True})
  return jobs

def run_jobs(jobs: list) -> list:
  out = []
  for j in jobs:
    fn = j["fn"]
    if j["cls"] == "FOOTING":
      names = {i.name for i in j["inputs"]}
      fn = RX.strip_footing if "strip_length_ft" in names or "length_in" not in names else RX.pad_footing
    ledger = RX.Ledger(j["inputs"])
    out.append((j, fn(ledger, j["mark"], j["floor"])))
  return out
