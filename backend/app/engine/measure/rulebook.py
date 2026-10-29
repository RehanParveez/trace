from __future__ import annotations
import pathlib
import contextvars
import json
import os
from dataclasses import dataclass
from contextlib import contextmanager

PRINTED, STANDARD, JUDGEMENT = "PRINTED", "STANDARD", "JUDGEMENT"
CLASSES = (PRINTED, STANDARD, JUDGEMENT)
COMPANY, QS_WORKBOOK, PROJECT, CODE_DEFAULT_ASSUMED = "COMPANY", "QS_WORKBOOK", "PROJECT", "CODE_DEFAULT_ASSUMED"
PRINTED_ORIGIN = "PRINTED"
PRINTED_OVER_COMPANY_RULE = "PRINTED_OVER_COMPANY_RULE"
SEED_FILE = pathlib.Path(__file__).with_name("rule_seed.yaml")
ENV_SWITCH = "TRACE_RULEBOOK"

@dataclass(frozen=True)
class RuleValue:
  value: object
  unit: str | None
  cls: str
  origin: str
  rule_id: str | None
  version: int

def enabled() -> bool:
  return os.environ.get(ENV_SWITCH, "on").strip().lower() != "off"

def _seed_id(key: str, scope: dict) -> str:
  return f"seed:{key}" + ("[" + ",".join(f"{k}={scope[k]}" for k in sorted(scope)) + "]" if scope else "")

def _load_seed() -> tuple:
  import yaml
  raw = yaml.safe_load(SEED_FILE.read_text(encoding="utf-8")) or {}
  version = int(raw.get("version") or 1)
  out: dict = {}
  scoped: dict = {}
  for r in raw.get("rules") or []:
    key, scope = str(r["key"]), dict(r.get("scope") or {})
    rv = RuleValue(r.get("value"), r.get("unit"), r.get("cls") or JUDGEMENT, CODE_DEFAULT_ASSUMED, _seed_id(key, scope), version)
    scoped.setdefault(key, []).append((scope, rv))
    if not scope or key not in out:
      out[key] = rv
  for lst in scoped.values():
    lst.sort(key=lambda t: (-len(t[0]), json.dumps(t[0], sort_keys=True)))
  return out, version, scoped, dict(raw.get("qs") or {})

SEED, SEED_VERSION, SEED_ROWS, QS_SEED = _load_seed()

UNVERIFIED_SOURCE = "common practice, clause not verified"
SOURCE_FORMS = ("verified: ", "exact ", "derived ")     

def _load_sources() -> dict:
  import yaml
  raw = yaml.safe_load(SEED_FILE.read_text(encoding="utf-8")) or {}
  return {str(r["key"]): str(r["source"]) for r in raw.get("rules") or [] if r.get("source")}

SOURCES = _load_sources()

_ROWS = contextvars.ContextVar("rule_book_rows", default=None)
_OVER = contextvars.ContextVar("rule_book_overrides", default=None)
_USED = contextvars.ContextVar("rule_book_used", default=None)
_CLASHES = contextvars.ContextVar("rule_book_clashes", default=None)
_BOOK = contextvars.ContextVar("rule_book_ref", default=None)
_CASE = contextvars.ContextVar("rule_book_case", default=None)
LEGACY = None

def _scope_of(raw) -> dict:
  return dict(raw) if isinstance(raw, dict) else {}

def _index(rows) -> dict:
  out: dict = {}
  for r in rows or []:
    if r.get("value") is None:
      continue
  
    scope = _scope_of(r.get("scope"))
    rv = RuleValue(r["value"], r.get("unit"), r.get("cls") or JUDGEMENT, r.get("origin") or COMPANY, str(r["id"]) if r.get("id") is not None else None, int(r.get("version") or 1))
    out.setdefault(str(r["key"]), []).append((scope, rv))
  for lst in out.values():
    lst.sort(key=lambda t: (-len(t[0]), json.dumps(t[0], sort_keys=True)))
  return out

def _matches(row_scope: dict, scope: dict) -> bool:
  return all(k in scope and scope[k] == v for k, v in row_scope.items())

def _best(rows: list | None, scope: dict, origins: tuple | None = None) -> RuleValue | None:
  for row_scope, rv in rows or ():
    if (origins is None or rv.origin in origins) and _matches(row_scope, scope):
      return rv
  return None

def hold(book: dict | None) -> None:
  book = book or {}
  _ROWS.set(_index(book.get("rows")))
  _OVER.set(_index(book.get("overrides")))
  _BOOK.set(book.get("book"))
  _USED.set({})
  _CLASHES.set([])

def hold_layer(layer: dict | None) -> None:
  rows = [{"id": f"company:{k}", "key": k, "scope": {}, "value": v.get("value"), "cls": JUDGEMENT, "origin": v.get("origin") or COMPANY, "version": 1}
    for k, v in (layer or {}).items() if isinstance(v, dict) and v.get("value") is not None]
  _ROWS.set(_index(rows))
  _OVER.set({})
  _BOOK.set(None)
  _USED.set({})
  _CLASHES.set([])

@contextmanager
def using(book_rows=None, overrides=None):
  tokens = (_ROWS.set(_index(book_rows)), _OVER.set(_index(overrides)), _USED.set({}), _CLASHES.set([]), _BOOK.set(None))
  try:
    yield
  finally:
    for var, tok in zip((_ROWS, _OVER, _USED, _CLASHES, _BOOK), tokens):
      var.reset(tok)

@contextmanager
def using_layer(layer: dict | None):
  saved = (_ROWS.get(), _OVER.get(), _BOOK.get())
  hold_layer(layer)
  try:
    yield
  finally:
    _ROWS.set(saved[0]); _OVER.set(saved[1]); _BOOK.set(saved[2])

def _rows(key: str) -> list:
  case = (_CASE.get() or {}).get(key) or []
  book = (_ROWS.get() or {}).get(key) or []
  if not case:
    return book
  return sorted(case + book, key=lambda t: -len(t[0])) if book else case

def _seed_best(key: str, scope: dict | None) -> RuleValue | None:
  for row_scope, rv in SEED_ROWS.get(key, ()):
    if _matches(row_scope, scope or {}):
      return rv
  return None

def lookup(key: str, scope: dict | None = None) -> RuleValue | None:
  """The rule in force for a key and scope in the project override, then the company, then the QS workbook rows (the case's rules count with the book's), with nothing recorded; None when only the seed (or nothing) holds it."""
  scope = scope or {}
  rows = _rows(key)
  return _best((_OVER.get() or {}).get(key), scope) or _best(rows, scope, (COMPANY,)) or _best(rows, scope, (QS_WORKBOOK,)) or _best(rows, scope)

def _note_used(rv: RuleValue) -> None:
  used = _USED.get()
  if used is None:
    used = {}
    _USED.set(used)
  used[(rv.rule_id, rv.version)] = None

def _differs(a, b) -> bool:
  try:
    return abs(float(a) - float(b)) > 1e-9
  except (TypeError, ValueError):
    return str(a) != str(b)

def resolve(key: str, scope: dict | None = None, printed=None, record: bool = True) -> RuleValue:
  held = lookup(key, scope)
  if printed is not None:
    seed = SEED.get(key)
    rv = RuleValue(printed, (held or seed).unit if (held or seed) else None, PRINTED, PRINTED_ORIGIN, None, 0)
    if held is not None and held.origin in (COMPANY, PROJECT) and _differs(held.value, printed):
      clashes = _CLASHES.get()
      if clashes is None:
        clashes = []
        
        _CLASHES.set(clashes)
      clashes.append({"key": key, "printed": printed, "rule": held.value, "origin": held.origin, "rule_id": held.rule_id, "version": held.version})
    return rv
  rv = held or _seed_best(key, scope) or SEED.get(key) or RuleValue(None, None, STANDARD, CODE_DEFAULT_ASSUMED, None, 0)
  if record and rv.rule_id is not None:
    _note_used(rv)
  return rv

def pick(key: str, default, scope: dict | None = None):
  """The figure for a key: the rule in force when there is one, else the caller's own default (the seed holds the same figure; seed_problems checks it). With TRACE_RULEBOOK=off the company layer answers as it did before the rule book."""
  if not enabled():
    held = LEGACY(key) if LEGACY is not None else None
    return default if held is None else held
  rv = resolve(key, scope)
  return default if rv.origin == CODE_DEFAULT_ASSUMED else rv.value

def qs() -> dict:
  """The QS whose answers the QS workbook figures are: name and the dates of the answers. A book held by hold() may carry its own under "qs"; otherwise the seed file's."""
  book = _BOOK.get()
  return {**QS_SEED, **((book.get("qs") if isinstance(book, dict) else None) or {})}

@contextmanager
def using_case(rows):
  """Hold the rules of a case (what load_rules gives) for a block, beside the book and the company's: the offline runner's way of running a case under its own company rules."""
  token = _CASE.set(_index(rows))
  try:
    yield
  finally:
    _CASE.reset(token)

def load_rules(path) -> tuple:
  import yaml
  from app.engine.measure import readings
  from app.modules.drawings_boq.takeoff.extract import finish_rules as FR
  path = pathlib.Path(path)
  raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
  default_origin = str(raw.get("origin") or QS_WORKBOOK).upper()
  known = {r["key"] for r in readings.registry()}
  rows, problems = [], []
  
  for i, r in enumerate(raw.get("rules") or [], 1):
    where = f"{path.name}, rule {i}"
    key, scope = str(r.get("key") or ""), dict(r.get("scope") or {})
    if str(r.get("status") or "").upper() == "DRAFT" and not r.get("confirmed_by"):
      problems.append(f"{where}: {key or 'a rule'} is a DRAFT drafted from a workbook and not confirmed by a person; it is not used.")
      continue
    cls, origin = str(r.get("cls") or JUDGEMENT).upper(), str(r.get("origin") or default_origin).upper()
    if cls not in CLASSES or origin not in (COMPANY, QS_WORKBOOK):
      problems.append(f"{where}: class {cls} or origin {origin} is not one the book holds.")
      continue
    if key in FR.KEYS:
      try:
        value = FR.checked(key, scope, r.get("value"))
      except ValueError as exc:
        problems.append(f"{where}: {exc}")
        continue
    elif key.startswith("formula."):
      from app.engine.measure import rule_formulas as RF
      try:
        value = RF.checked(r.get("value"))
      except ValueError as exc:
        problems.append(f"{where}: {exc}")
        continue
    elif key in known:
      value = r.get("value")
    else:
      problems.append(f"{where}: {key or 'a rule with no key'} is not a rule key.")
      continue
    rows.append({"id": f"{path.name}:{i}", "key": key, "scope": scope, "value": value, "unit": r.get("unit"), "cls": cls, "origin": origin, "version": 1, "note": r.get("note")})
  return rows, problems

def mark() -> int:
  return len(_USED.get() or {})

def stamp(since: int = 0) -> list:
  return [{"id": i, "version": v} for i, v in list(_USED.get() or {})[since:]]

def clashes(since: int = 0) -> list:
  return list(_CLASHES.get() or [])[since:]

def clash_mark() -> int:
  return len(_CLASHES.get() or [])

def book_ref() -> dict | None:
  return _BOOK.get()

def _same(a, b) -> bool:
  if a is None or b is None:
    return a is None and b is None
  if isinstance(a, (list, dict)) or isinstance(b, (list, dict)):
    return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
  return not _differs(a, b)

def seed_problems() -> list:
  from app.engine.measure import readings
  out: list = []
  
  for row in readings.registry():
    s = SEED.get(row["key"])
    if s is None:
      out.append((row["key"], "missing from the seed"))
    elif not _same(s.value, row["default"]):
      out.append((row["key"], f"seed {s.value!r}, code {row['default']!r}"))
  for key, expected in proposed_values().items():
    s = SEED.get(key)
    if s is None:
      out.append((key, "missing from the seed"))
    elif not _same(s.value, expected):
      out.append((key, f"seed {s.value!r}, code {expected!r}"))
  from app.modules.drawings_boq.takeoff.extract import finish_rules as FR
  for key, expected in FR.seed_expect().items():
    s = next((rv for scope, rv in SEED_ROWS.get(key, ()) if not scope), None)
    
    if s is None:
      out.append((key, "missing from the seed"))
    elif not _same(s.value, expected):
      out.append((key, f"seed {s.value!r}, code {expected!r}"))
  for key in FR.KEYS:
    for scope, rv in SEED_ROWS.get(key, ()):
      try:
        FR.checked(key, scope, rv.value)
      except ValueError as exc:
        out.append((rv.rule_id, str(exc)))
  from app.engine.measure import stages as STG
  for key, expected in STG.seed_expect().items():
    s = next((rv for scope, rv in SEED_ROWS.get(key, ()) if not scope), None)
    if s is None:
      out.append((key, "missing from the seed"))
    elif not _same(s.value, expected):
      out.append((key, f"seed {s.value!r}, code {expected!r}"))
  from app.engine.measure import steel_rules as SRL
  for key, expected in SRL.seed_expect().items():
    s = SEED.get(key)
    if s is None:
      out.append((key, "missing from the seed"))
    elif not _same(s.value, expected):
      out.append((key, f"seed {s.value!r}, code {expected!r}"))
  for key, rv in SEED.items():
    if rv.cls != STANDARD:
      continue
    src = SOURCES.get(key)
    if not src:
      out.append((key, f"a STANDARD row needs a source: the standard and clause it was checked in, or '{UNVERIFIED_SOURCE}'"))
    elif src != UNVERIFIED_SOURCE and not src.startswith(SOURCE_FORMS):
      out.append((key, f"source {src!r} is not '{UNVERIFIED_SOURCE}' and does not say what text it was verified in (verified: ...)"))
  for field in ("name", "answered_before", "answered_on", "latest"):
    if not QS_SEED.get(field):
      out.append((f"qs.{field}", "missing from the seed"))
  return out

def proposed_values() -> dict:
  from app.engine.measure import proposed as P
  return {
    "working_space_qs_mm": P.WORKING_SPACE_QS_MM, "props_step_mm": P.PROPS_STEP_MM, "arch_rise_ratio": P.ARCH_RISE_RATIO, "arch_wall_mm": P.ARCH_WALL_MM,
    "concrete_dry_factor": P.CONCRETE_DRY_FACTOR, "mortar_dry_factor": P.MORTAR_DRY_FACTOR, "plaster_dry_factor": P.PLASTER_DRY_FACTOR, "bag_kg": P.BAG_KG,
    "cement_kg_m3": P.CEMENT_KG_M3, "brick_mm": list(P.BRICK_MM), "joint_mm": P.JOINT_MM, "default_rcc_mix": list(P.DEFAULT_RCC_MIX), "default_pcc_mix": list(P.DEFAULT_PCC_MIX),
    "default_brick_mortar": list(P.DEFAULT_BRICK_MORTAR), "default_plaster_mortar": list(P.DEFAULT_PLASTER_MORTAR),
    "nominal_mix_by_grade": {k: list(v) for k, v in P.NOMINAL_MIX_BY_GRADE.items()}, "nominal_mix_by_psi": {k: list(v) for k, v in P.NOMINAL_MIX_BY_PSI.items()},
    "bare_figure_inches_below": P.BARE_FIGURE_INCHES_BELOW, "raft_pcc_mm": P.RAFT_PCC_MM, "brick_step_offset_mm": P.BRICK_STEP_OFFSET_MM,
    "brick_step_heights_mm": {k: list(v) for k, v in P.BRICK_STEP_HEIGHTS_MM.items()},
    "cft_per_m3": 35.3146667, "sft_per_m2": 10.7639104,
  }
