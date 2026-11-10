from __future__ import annotations
import re
from dataclasses import dataclass

SECTIONS = {
  "EW": "Earthwork and substructure",
  "RC": "Concrete and RCC members",
  "RF": "Reinforcement and formwork",
  "MS": "Masonry",
  "DP": "Damp proofing, waterproofing, termite, insulation and roof",
  "PL": "Plaster, wall and ceiling finishes, paint",
  "FL": "Floors, skirting and stair finishes",
  "DW": "Doors, windows, glazing, railings and metalwork",
  "KJ": "Kitchen, wardrobes, fixtures and joinery",
  "PB": "Plumbing, drainage, water supply and sanitary",
  "EL": "Electrical and low voltage",
  "EX": "External works",
  "PZ": "Plaza and commercial additions",
  "NR": "Items that are not read from drawings",
}
USES = ("H", "P")
UNITS = ("cft", "sft", "rft", "nos", "kg", "kw", "lump_sum", "percent", "day")
INPUT_UNITS = UNITS + ("mm", "m", "ft", "in", "mm2", "text")
SOURCES = ("SCHEDULE", "PLAN_LABEL", "LAYOUT", "SECTION", "DETAIL", "STOREY", "LEVELS", "LEGEND", "NOTE", "SPEC", "DECISION", "CONVENTION", "DERIVED", "ELEVATION", "TABLE", "SYMBOL_COUNT", "RATE_BOOK")
SPLITS = ("floor", "dia", "mix", "size", "type", "room", "tank", "run")
MEMBER_CLASSES = (
  "EARTHWORK", "FOOTING_PAD", "FOOTING_STRIP", "FOOTING_OTHER", "PLINTH_BEAM", "COLUMN", "BEAM", "SLAB_PANEL", "LINTEL_TYPE", "STRUCT_WALL", "STAIR", "TANK", "PARAPET",
  "REINFORCEMENT", "FORMWORK", "WALL", "BOUNDARY_WALL", "OPENING", "ROOM", "FINISH_LAYER", "FIXTURE", "JOINERY", "FITTING", "POINT", "PIPE_RUN", "SITE_AREA", "ROOF_LAYER", "WATERPROOFING", "METALWORK", "ALLOWANCE",
)
PAGE_ROLES = (
  "SITE_PLAN", "FOOTING_LAYOUT", "EXCAVATION_PLAN", "BASEMENT_PLAN", "RAFT_PLAN", "PILE_LAYOUT", "COLUMN_LAYOUT", "COLUMN_SCHEDULE", "BEAM_LAYOUT", "SLAB_PLAN", "STRUCTURAL_PLAN",
  "FLOOR_PLAN", "ROOF_PLAN", "ELEVATION", "SECTION", "DETAIL", "LINTEL_TABLE", "STAIR_DETAIL", "TANK_DETAIL", "SEPTIC_DETAIL", "TOILET_DETAIL", "KITCHEN_DETAIL", "FURNITURE_PLAN",
  "CEILING_PLAN", "OPENING_SCHEDULE", "FINISH_SCHEDULE", "ELECTRICAL_PLAN", "SINGLE_LINE_DIAGRAM", "LOW_VOLTAGE_PLAN", "PLUMBING_PLAN", "DRAINAGE_PLAN", "ISOMETRIC", "GAS_PLAN", "FIRE_PLAN",
  "FACADE", "HVAC_PLAN", "PARKING_PLAN", "BOUNDARY_DETAIL", "GATE_DETAIL", "SPEC", "SOIL_REPORT", "GENERAL_NOTES", "INTERIOR_DRAWINGS", "REINFORCEMENT_SCHEDULE",
)
READER_CLASSES = (
  "GRID", "COLUMN", "FOOTING_STRIP", "FOOTING_PAD", "PLINTH_BEAM", "WALL", "ROOM", "DOOR", "WINDOW", "BEAM", "SLAB_PANEL", "SLAB_BAR_CALLOUT", "ELECTRICAL_POINT", "DISTRIBUTION_BOARD",
  "PLUMBING_FIXTURE", "PIPE_RUN", "DRAIN_POINT", "COLUMN_SCHEDULE_CELL", "NOTE_FACT", "LINTEL_TYPE", "STAIR", "TANK",
)
READ_SHEETS = ("PLAN/COLUMN_LAYOUT", "PLAN/FOOTING_LAYOUT", "PLAN/FOUNDATION", "PLAN/FLOOR", "PLAN/SLAB", "PLAN/OVERLAY", "SCHEDULE", "NOTES")
STATES = ("MEASURED", "ASSUMED", "ASKED", "NOT_APPLICABLE", "NOT_READ")
FACT_KEYS = ("type", "structure", "basement", "floors_min", "sets_present")
FACT_VALUES = {
  "type": ("HOUSE", "PLAZA"),
  "structure": ("RCC_FRAME", "LOAD_BEARING", "STEEL_FRAME"),
  "sets_present": ("ARCHITECTURE", "STRUCTURE", "ELECTRICAL", "PLUMBING", "HVAC", "FIRE", "INTERIOR"),
}
BILLING_KINDS = ("MRS_PB", "PRIVATE_QS")
OWNER_RE = re.compile(r"^(CV-\d+|BB-\d+|PX-\d+|CT-\d+|BM-\d+|RATE|DERIVED)$")
ID_RE = re.compile(r"^([A-Z]{2})-(\d{2})$")
MEASURED_BY_FAMILY, BY_RECIPE, DERIVED_ROAD, ASK_ONLY = "MEASURED_BY_FAMILY", "BY_RECIPE", "DERIVED", "ASK_ONLY"
ROAD_STATUSES = (MEASURED_BY_FAMILY, BY_RECIPE, DERIVED_ROAD, ASK_ONLY)
RECIPES = ("wall_face", "floor_area", "wall_run", "member_volume", "member_contact", "excavation", "layers", "counts", "openings_area", "site", "pipe_run")
ITEM_FIELDS = ("id", "name", "section", "use", "unit", "member_class", "inputs", "yields", "page_roles", "applies_when", "owner_pack", "derived", "billing", "how_measured", "status_v1", "status_v1_was", "recipe", "reads")

@dataclass(frozen=True)
class Input:
  name: str
  sources: tuple
  unit: str | None = None
  default_rule: str | None = None

@dataclass(frozen=True)
class Yield:
  qty: str
  unit: str
  split: tuple = ()

@dataclass(frozen=True)
class Read:
  cls: str
  on: tuple = ()
  support: bool = False

@dataclass(frozen=True)
class MrsLine:
  item: str
  qty: str
  spec: str | None = None
  convert: str | None = None

@dataclass(frozen=True)
class QsLine:
  line: str
  qty: str

@dataclass(frozen=True)
class Billing:
  MRS_PB: tuple = ()
  PRIVATE_QS: tuple = ()

@dataclass(frozen=True)
class Item:
  id: str
  name: str
  section: str
  use: tuple
  unit: str
  member_class: str
  inputs: tuple
  yields: tuple
  page_roles: tuple
  applies_when: dict
  owner_pack: str
  derived: dict | None
  billing: Billing
  how_measured: str = ""
  status_v1: str = ""
  recipe: str = ""
  reads: tuple = ()

  def as_dict(self) -> dict:
    return {
      "id": self.id, "name": self.name, "section": self.section, "use": list(self.use), "unit": self.unit, "member_class": self.member_class,
      "inputs": [{"name": i.name, "unit": i.unit, "sources": list(i.sources), "default_rule": i.default_rule} for i in self.inputs],
      "yields": [{"qty": y.qty, "unit": y.unit, "split": list(y.split)} for y in self.yields],
      "page_roles": list(self.page_roles), "applies_when": dict(self.applies_when), "owner_pack": self.owner_pack, "derived": self.derived,
      "billing": {"MRS_PB": [{"item": b.item, "qty": b.qty, "spec": b.spec, "convert": b.convert} for b in self.billing.MRS_PB],
        "PRIVATE_QS": [{"line": b.line, "qty": b.qty} for b in self.billing.PRIVATE_QS]},
      "how_measured": self.how_measured, "status_v1": self.status_v1, "recipe": self.recipe,
      "reads": [{"class": r.cls, "on": list(r.on), "support": r.support} for r in self.reads],
    }

def parse(raw: dict) -> Item:
  """One catalogue entry as written in elements.yaml, as an Item. A missing key raises KeyError, which `validate` reports as a problem."""
  billing = raw.get("billing") or {}
  return Item(
    id=str(raw["id"]), name=str(raw["name"]), section=str(raw["section"]), use=tuple(raw["use"]), unit=str(raw["unit"]), member_class=str(raw["member_class"]),
    inputs=tuple(Input(name=str(i["name"]), sources=tuple(i.get("sources") or ()), unit=i.get("unit"), default_rule=i.get("default_rule")) for i in raw.get("inputs") or []),
    yields=tuple(Yield(qty=str(y["qty"]), unit=str(y["unit"]), split=tuple(y.get("split") or ())) for y in raw.get("yields") or []),
    page_roles=tuple(raw.get("page_roles") or ()), applies_when=dict(raw.get("applies_when") or {}), owner_pack=str(raw["owner_pack"]), derived=raw.get("derived"),
    billing=Billing(
      MRS_PB=tuple(MrsLine(item=str(b["item"]), qty=str(b["qty"]), spec=b.get("spec"), convert=b.get("convert")) for b in billing.get("MRS_PB") or []),
      PRIVATE_QS=tuple(QsLine(line=str(b["line"]), qty=str(b["qty"])) for b in billing.get("PRIVATE_QS") or []),
    ),
    how_measured=str(raw.get("how_measured") or ""), status_v1=str(raw.get("status_v1") or ""), recipe=str(raw.get("recipe") or ""),
    reads=tuple(Read(cls=str(r["class"]), on=tuple(r.get("on") or ()), support=bool(r.get("support", False))) for r in raw.get("reads") or []),
  )

def _facts_problems(item_id: str, facts: dict) -> list:
  out = []
  for k, v in facts.items():
    if k not in FACT_KEYS:
      out.append(f"{item_id}: applies_when names {k}, which is not a project fact ({', '.join(FACT_KEYS)})")
    elif k in FACT_VALUES:
      values = v if isinstance(v, list) else [v]
      bad = [x for x in values if x not in FACT_VALUES[k]]
      if bad:
        out.append(f"{item_id}: applies_when {k} has {', '.join(map(str, bad))}; allowed {', '.join(FACT_VALUES[k])}")
    elif k == "basement" and not isinstance(v, bool):
      out.append(f"{item_id}: applies_when basement must be true or false")
    elif k == "floors_min" and not (isinstance(v, int) and not isinstance(v, bool) and v >= 1):
      out.append(f"{item_id}: applies_when floors_min must be a whole number from 1")
  return out

def validate(raws: list, rule_ids: set | None = None) -> list:
  """Everything wrong with the catalogue: a missing field, an unknown unit, source, page role or member class, a billing entry that points at no yield, an owner that is neither a pack, DERIVED nor RATE, a derived item without its rule, a duplicate id."""
  out: list = []
  seen: dict = {}
  items: dict = {}
  for n, raw in enumerate(raws, 1):
    label = str(raw.get("id") or f"entry {n}") if isinstance(raw, dict) else f"entry {n}"
    if not isinstance(raw, dict):
      out.append(f"{label}: not a mapping")
      continue
    missing = [f for f in ("id", "name", "section", "use", "unit", "member_class", "yields", "owner_pack", "billing") if f not in raw or raw[f] in (None, "")]
    if missing:
      out.append(f"{label}: missing {', '.join(missing)}")
      continue
    try:
      it = parse(raw)
    except (KeyError, TypeError) as e:
      out.append(f"{label}: cannot be read ({e})")
      continue
    if it.id in seen:
      out.append(f"{it.id}: id used twice")
    seen[it.id] = True
    items[it.id] = it
    m = ID_RE.match(it.id)
    if not m or m.group(1) not in SECTIONS:
      out.append(f"{it.id}: the id is not a section prefix ({', '.join(SECTIONS)}) and two digits")
    elif SECTIONS[m.group(1)] != it.section:
      out.append(f"{it.id}: section {it.section!r} does not belong to prefix {m.group(1)}")
    if not it.use or any(u not in USES for u in it.use):
      out.append(f"{it.id}: use must be H, P or both")
    if it.member_class not in MEMBER_CLASSES:
      out.append(f"{it.id}: member_class {it.member_class} is not one of the known classes")
    if it.status_v1 not in ROAD_STATUSES:
      out.append(f"{it.id}: status_v1 is {it.status_v1!r}; it is one of {', '.join(ROAD_STATUSES)}")
    if (it.status_v1 == BY_RECIPE) != bool(it.recipe):
      out.append(f"{it.id}: a recipe is named exactly when status_v1 is {BY_RECIPE}")
      
    if not it.yields:
      out.append(f"{it.id}: no yield")
    for y in it.yields:
      if y.unit not in UNITS:
        out.append(f"{it.id}: yield {y.qty} has unit {y.unit}, which is not one of {', '.join(UNITS)}")
      bad = [s for s in y.split if s not in SPLITS]
      if bad:
        out.append(f"{it.id}: yield {y.qty} splits by {', '.join(bad)}")
    if len({y.qty for y in it.yields}) != len(it.yields):
      out.append(f"{it.id}: two yields with the same name")
    names = [i.name for i in it.inputs]
    if len(set(names)) != len(names):
      out.append(f"{it.id}: two inputs with the same name")
    for i in it.inputs:
      if not i.sources or any(s not in SOURCES for s in i.sources):
        out.append(f"{it.id}: input {i.name} needs sources from {', '.join(SOURCES)}")
      if i.unit is not None and i.unit not in INPUT_UNITS:
        out.append(f"{it.id}: input {i.name} has unit {i.unit}")
      if i.default_rule and rule_ids is not None and i.default_rule not in rule_ids:
        out.append(f"{it.id}: input {i.name} names default rule {i.default_rule}, which is not in the rule registry")
    bad_roles = [r for r in it.page_roles if r not in PAGE_ROLES]
    if bad_roles:
      out.append(f"{it.id}: page role {', '.join(bad_roles)} is unknown")
    if not it.page_roles and it.owner_pack not in ("RATE", "DERIVED"):
      out.append(f"{it.id}: no page role, and the item is drawn")
    if it.page_roles and it.owner_pack in ("RATE",):
      out.append(f"{it.id}: a rate-only item has page roles")
    for r in it.reads:
      if r.cls not in READER_CLASSES:
        out.append(f"{it.id}: reads {r.cls}, which is not a reader class")
      bad_on = [k for k in r.on if k not in READ_SHEETS]
      if bad_on:
        out.append(f"{it.id}: reads {r.cls} on {', '.join(bad_on)}, which is not a sheet kind")
    if len({r.cls for r in it.reads}) != len(it.reads):
      out.append(f"{it.id}: the same reader class twice")
    if it.reads and it.owner_pack in ("RATE", "DERIVED"):
      out.append(f"{it.id}: a rate-only or derived item has no reader")
    out.extend(_facts_problems(it.id, it.applies_when))
    if not OWNER_RE.match(it.owner_pack):
      out.append(f"{it.id}: owner {it.owner_pack} is not a pack, DERIVED or RATE")
    if it.owner_pack == "DERIVED" and not (isinstance(it.derived, dict) and it.derived.get("from") and it.derived.get("rule")):
      out.append(f"{it.id}: a DERIVED item names {{from, rule}}")
    qtys = {y.qty for y in it.yields}
    for b in it.billing.MRS_PB:
      if b.qty not in qtys:
        out.append(f"{it.id}: rate-book entry {b.item} points at {b.qty}, which is not a yield")
    for b in it.billing.PRIVATE_QS:
      if b.qty not in qtys:
        out.append(f"{it.id}: line {b.line} points at {b.qty}, which is not a yield")
    if set(raw.get("billing") or {}) - set(BILLING_KINDS):
      out.append(f"{it.id}: billing has a kind other than {', '.join(BILLING_KINDS)}")
  for it in items.values():
    if it.derived:
      src = it.derived.get("from")
      for s in (src if isinstance(src, list) else [src]):
        if s not in items:
          out.append(f"{it.id}: derived from {s}, which is not an item")
  return out

def expected_classes(items: list) -> dict:
  """The classes a sheet kind is expected to show, in the order of READER_CLASSES: what the items read on that kind of sheet. Replaces a hand-kept table."""
  found: dict = {}
  for it in items:
    for r in it.reads:
      for key in r.on:
        found.setdefault(key, set()).add(r.cls)
  return {key: tuple(c for c in READER_CLASSES if c in classes) for key, classes in found.items()}
