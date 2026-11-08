from __future__ import annotations
import os
import re
import shutil
import tempfile
from dataclasses import dataclass, field
from app.modules.drawings_boq.takeoff.run import vocab as V
import yaml

FILES = ("document.yaml", "register.yaml", "elements.yaml", "joins.yaml", "params.yaml", "truth_log.yaml")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
KEY_LEN = 12
MARK_KINDS = ("SIZE",)
SIZE_CLASSES = ("DOOR", "WINDOW")
DRAFT_SOURCE = "draft"
CHECKED_SOURCE = "checked"

class TruthFormatError(ValueError):
  def __init__(self, problems: list):
    self.problems = problems
    super().__init__("\n".join(f"{p['file']}, {p['row']}, {p['field']}: {p['message']}" for p in problems))

@dataclass
class TruthStamp:
  by: V.TruthSource
  checked: bool | None
  source: str
  date: str
  note: str | None = None
  checked_by: str | None = None
  checked_date: str | None = None

@dataclass
class DocumentProfile:
  alias: str
  split: V.Split
  sha256: str
  pages: int
  case: str
  consultant: str | None = None
  producer: str | None = None
  units: str = "UNKNOWN"

@dataclass
class RegisterRow:
  sheet: int
  role: V.Role
  text_type: V.TextType
  truth: TruthStamp
  sheet_no: str | None = None
  title: str | None = None
  plan_kind: V.PlanKind | None = None
  floor: str | None = None
  discipline: str | None = None
  scale_ratio: float | None = None
  scale_basis: str | None = None
  was: dict | None = None

@dataclass
class ElementRow:
  sheet: int
  cls: V.ElementClass
  truth: TruthStamp
  mark: str | None = None
  at: dict | None = None
  geom: dict | None = None
  attrs: dict = field(default_factory=dict)
  conflict: dict | None = None
  mark_kind: str | None = None
  was: dict | None = None

@dataclass
class JoinRow:
  kind: V.JoinKind
  src: dict
  dst: dict
  truth: TruthStamp | None = None
  was: dict | None = None

@dataclass
class ParamRow:
  element: dict
  inputs: dict
  qs_line: list = field(default_factory=list)

@dataclass
class TruthSet:
  folder: str
  document: DocumentProfile
  register: list = field(default_factory=list)
  elements: list = field(default_factory=list)
  joins: list = field(default_factory=list)
  params: list = field(default_factory=list)
  log: list = field(default_factory=list)

class _Problems:
  def __init__(self):
    self.items: list = []

  def add(self, file: str, row, field_name: str, message: str) -> None:
    self.items.append({"file": file, "row": row, "field": field_name, "message": message})

def _read(folder: str, name: str, problems: _Problems, want):
  path = os.path.join(folder, name)
  if not os.path.isfile(path):
    problems.add(name, "-", "-", "the file is missing")
    return want()
  try:
    with open(path, encoding="utf-8") as fh:
      doc = yaml.safe_load(fh)
  except yaml.YAMLError as exc:
    problems.add(name, "-", "-", f"not valid YAML: {str(exc).splitlines()[0]}")
    return want()
  if doc is None:
    return want()
  if not isinstance(doc, want):
    problems.add(name, "-", "-", f"must be a {'mapping' if want is dict else 'list'}")
    return want()
  return doc

def _enum(cls, value, file: str, row, name: str, problems: _Problems):
  try:
    return cls.parse(value)
  except ValueError as exc:
    problems.add(file, row, name, str(exc))
    return None

def _only(entry: dict, allowed: tuple, file: str, row, problems: _Problems) -> None:
  for key in entry:
    if key not in allowed:
      problems.add(file, row, key, f"unknown field; allowed: {', '.join(allowed)}")

def _was(entry: dict, file: str, row, problems: _Problems):
  was = entry.get("was")
  if was is not None and not isinstance(was, dict):
    problems.add(file, row, "was", "must be a mapping of field name to the value it had before a person corrected it")
    return None
  return was

def _stamp(entry, file: str, row, problems: _Problems, required: bool) -> TruthStamp | None:
  if entry is None:
    if required:
      problems.add(file, row, "truth", "is missing")
    return None
  if not isinstance(entry, dict):
    problems.add(file, row, "truth", "must be a mapping")
    return None
  _only(entry, ("by", "checked", "source", "date", "note", "checked_by", "checked_date"), file, row, problems)
  by = _enum(V.TruthSource, entry.get("by"), file, row, "truth.by", problems)
  checked = entry.get("checked")

  if checked is not None and not isinstance(checked, bool):
    problems.add(file, row, "truth.checked", "must be true, false or empty")
    checked = None
  source = entry.get("source")
  if not isinstance(source, str) or not source:
    problems.add(file, row, "truth.source", "is missing")
    source = ""
  date = str(entry.get("date") or "")
  if not DATE.match(date):
    problems.add(file, row, "truth.date", "must be a date written YYYY-MM-DD")
  if by is None:
    return None
  checked_by, checked_date = entry.get("checked_by"), entry.get("checked_date")
  if checked_by is not None and (not isinstance(checked_by, str) or not checked_by.strip()):
    problems.add(file, row, "truth.checked_by", "must be the name of the person who checked")
    checked_by = None
  if checked_date is not None and not DATE.match(str(checked_date)):
    problems.add(file, row, "truth.checked_date", "must be a date written YYYY-MM-DD")
  if checked is True and (not checked_by or not checked_date):
    problems.add(file, row, "truth.checked", "a checked row needs checked_by and checked_date, so every check has a name and a day")
  return TruthStamp(by=by, checked=checked, source=source, date=date, note=entry.get("note"), checked_by=checked_by, checked_date=None if checked_date is None else str(checked_date))

def _page(value, pages: int, file: str, row, name: str, problems: _Problems) -> int | None:
  if isinstance(value, bool) or not isinstance(value, int):
    problems.add(file, row, name, "must be a page number")
    return None
  if pages and not 1 <= value <= pages:
    problems.add(file, row, name, f"page {value} is outside 1 to {pages}")
    return None
  return value

def _document(folder: str, problems: _Problems) -> DocumentProfile | None:
  doc = _read(folder, "document.yaml", problems, dict)
  if not doc:
    return None
  _only(doc, ("alias", "split", "sha256", "pages", "case", "consultant", "producer", "units"), "document.yaml", "-", problems)

  alias = doc.get("alias")
  if not isinstance(alias, str) or not alias:
    problems.add("document.yaml", "-", "alias", "is missing")
  split = _enum(V.Split, doc.get("split"), "document.yaml", "-", "split", problems)
  sha = str(doc.get("sha256") or "")

  if not re.fullmatch(r"[0-9a-f]{64}", sha):
    problems.add("document.yaml", "-", "sha256", "must be 64 hexadecimal characters")
  elif os.path.basename(os.path.normpath(folder)) != sha[:KEY_LEN]:
    problems.add("document.yaml", "-", "sha256", f"the folder is named {os.path.basename(os.path.normpath(folder))}, the first {KEY_LEN} characters of the hash are {sha[:KEY_LEN]}")
  pages = doc.get("pages")
  if isinstance(pages, bool) or not isinstance(pages, int) or pages < 1:
    problems.add("document.yaml", "-", "pages", "must be a whole number of at least 1")
    pages = 0
  if split is None or not isinstance(alias, str):
    return None
  return DocumentProfile(alias=alias, split=split, sha256=sha, pages=pages, case=str(doc.get("case") or ""), consultant=doc.get("consultant"), producer=doc.get("producer"), units=str(doc.get("units") or "UNKNOWN"))

def _register(rows: list, pages: int, problems: _Problems) -> list:
  f, out, seen = "register.yaml", [], set()
  for i, e in enumerate(rows, 1):
    if not isinstance(e, dict):
      problems.add(f, i, "-", "must be a mapping")
      continue

    _only(e, ("sheet", "sheet_no", "title", "role", "plan_kind", "floor", "discipline", "scale_ratio", "scale_basis", "text_type", "truth", "was"), f, i, problems)
    sheet = _page(e.get("sheet"), pages, f, i, "sheet", problems)
    if sheet in seen:
      problems.add(f, i, "sheet", f"page {sheet} has two rows")
    seen.add(sheet)

    role = _enum(V.Role, e.get("role"), f, i, "role", problems)
    kind = None if e.get("plan_kind") in (None, "UNKNOWN") else _enum(V.PlanKind, e.get("plan_kind"), f, i, "plan_kind", problems)
    ttype = _enum(V.TextType, e.get("text_type"), f, i, "text_type", problems)
    ratio = e.get("scale_ratio")
    if ratio not in (None, "UNKNOWN") and (isinstance(ratio, bool) or not isinstance(ratio, (int, float)) or ratio <= 0):
      problems.add(f, i, "scale_ratio", "must be a positive number or UNKNOWN")
    stamp = _stamp(e.get("truth"), f, i, problems, True)
    if None not in (sheet, role, ttype, stamp):
      out.append(RegisterRow(sheet=sheet, role=role, text_type=ttype, truth=stamp, sheet_no=e.get("sheet_no"), title=e.get("title"), plan_kind=kind, floor=e.get("floor"), discipline=e.get("discipline"),
        scale_ratio=ratio if isinstance(ratio, (int, float)) and not isinstance(ratio, bool) else None, scale_basis=e.get("scale_basis"), was=_was(e, f, i, problems)))
  return out

def _at(at, f: str, i, problems: _Problems) -> None:
  if at is None:
    return
  if not isinstance(at, dict):
    problems.add(f, i, "at", "must be a mapping")
    return
  _only(at, ("page_xy", "grid"), f, i, problems)
  xy = at.get("page_xy")
  if xy is not None and not (isinstance(xy, list) and len(xy) == 2 and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in xy)):
    problems.add(f, i, "at.page_xy", "must be [x, y] in PDF points")
  grid = at.get("grid")
  if grid is not None and not (isinstance(grid, list) and len(grid) == 2):
    problems.add(f, i, "at.grid", "must be [row, line]")

def _geom(geom, f: str, i, problems: _Problems) -> None:
  if geom is None:
    return
  if not isinstance(geom, dict) or len(geom) != 1 or next(iter(geom)) not in ("point", "polyline", "polygon"):
    problems.add(f, i, "geom", "must hold exactly one of point, polyline or polygon")
    return
  kind, value = next(iter(geom.items()))
  need = {"point": 1, "polyline": 2, "polygon": 3}[kind]
  pts = [value] if kind == "point" else value
  if not isinstance(pts, list) or len(pts) < need or not all(isinstance(p, list) and len(p) == 2 for p in pts):
    problems.add(f, i, f"geom.{kind}", f"needs {need} or more [x, y] points" if kind != "point" else "must be [x, y]")

def _elements(rows: list, pages: int, problems: _Problems) -> list:
  f, out = "elements.yaml", []
  for i, e in enumerate(rows, 1):
    if not isinstance(e, dict):
      problems.add(f, i, "-", "must be a mapping")
      continue
  
    _only(e, ("sheet", "class", "mark", "mark_kind", "at", "geom", "attrs", "conflict", "truth", "was"), f, i, problems)
    sheet = _page(e.get("sheet"), pages, f, i, "sheet", problems)
    cls = _enum(V.ElementClass, e.get("class"), f, i, "class", problems)
    mark_kind = e.get("mark_kind")
    if mark_kind is not None:
      if mark_kind not in MARK_KINDS:
        problems.add(f, i, "mark_kind", f"must be one of {', '.join(MARK_KINDS)}")
        mark_kind = None
      elif cls is not None and cls.value not in SIZE_CLASSES:
        problems.add(f, i, "mark_kind", f"{mark_kind} applies to {' and '.join(SIZE_CLASSES)} only")
        mark_kind = None
      elif e.get("mark") is None:
        problems.add(f, i, "mark_kind", "a row with a mark kind needs the printed mark")
    _at(e.get("at"), f, i, problems)
    _geom(e.get("geom"), f, i, problems)
    attrs = e.get("attrs") or {}
    if not isinstance(attrs, dict):
      problems.add(f, i, "attrs", "must be a mapping")
      attrs = {}
      
    stamp = _stamp(e.get("truth"), f, i, problems, True)
    if None not in (sheet, cls, stamp):
      out.append(ElementRow(sheet=sheet, cls=cls, truth=stamp, mark=None if e.get("mark") is None else str(e["mark"]), at=e.get("at"), geom=e.get("geom"), attrs=attrs, 
       conflict=e.get("conflict"), mark_kind=mark_kind, was=_was(e, f, i, problems)))
  return out

def _ref(ref, f: str, i, name: str, pages: int, problems: _Problems) -> dict | None:
  if not isinstance(ref, dict):
    problems.add(f, i, name, "must be a mapping with sheet, class and mark or key")
    return None

  _only(ref, ("sheet", "class", "mark", "key"), f, i, problems)
  sheet = _page(ref.get("sheet"), pages, f, i, f"{name}.sheet", problems)
  cls = _enum(V.ElementClass, ref.get("class"), f, i, f"{name}.class", problems)
  if ref.get("mark") is None and ref.get("key") is None:
    problems.add(f, i, name, "needs a mark or a key")
  if sheet is None or cls is None:
    return None
  return {"sheet": sheet, "class": cls.value, "mark": None if ref.get("mark") is None else str(ref["mark"]), "key": None if ref.get("key") is None else str(ref["key"])}

def _joins(rows: list, pages: int, problems: _Problems) -> list:
  f, out = "joins.yaml", []
  for i, e in enumerate(rows, 1):
    if not isinstance(e, dict):
      problems.add(f, i, "-", "must be a mapping")
      continue
  
    _only(e, ("kind", "from", "to", "truth", "was"), f, i, problems)
    kind = _enum(V.JoinKind, e.get("kind"), f, i, "kind", problems)
    src = _ref(e.get("from"), f, i, "from", pages, problems)
    dst = _ref(e.get("to"), f, i, "to", pages, problems)
    stamp = _stamp(e.get("truth"), f, i, problems, False)
    if None not in (kind, src, dst):
      out.append(JoinRow(kind=kind, src=src, dst=dst, truth=stamp, was=_was(e, f, i, problems)))
  return out

def _params(rows: list, pages: int, problems: _Problems) -> list:
  f, out = "params.yaml", []
  for i, e in enumerate(rows, 1):
    if not isinstance(e, dict):
      problems.add(f, i, "-", "must be a mapping")
      continue
    _only(e, ("element", "inputs", "qs_line"), f, i, problems)
    qs_line = e.get("qs_line", [])
    if not isinstance(qs_line, list) or not all(isinstance(x, str) and x for x in qs_line):
      problems.add(f, i, "qs_line", "must be a list of line ids from the case expected.yaml")
      qs_line = []
    element = _ref(e.get("element"), f, i, "element", pages, problems)
    inputs = e.get("inputs")
    if not isinstance(inputs, dict) or not inputs:
      problems.add(f, i, "inputs", "must list at least one input")
      continue
  
    clean = {}
    for name, spec in inputs.items():
      if not isinstance(spec, dict):
        problems.add(f, i, f"inputs.{name}", "must be a mapping with a state")
        continue
      _only(spec, ("state", "value", "from", "note"), f, i, problems)
      state = _enum(V.ParamState, spec.get("state"), f, i, f"inputs.{name}.state", problems)
      if state is not None:
        clean[str(name)] = {"state": state.value, "value": spec.get("value"), "from": spec.get("from"), "note": spec.get("note")}
    if element is not None:
      out.append(ParamRow(element=element, inputs=clean, qs_line=qs_line))
  return out

def _log(rows: list, problems: _Problems) -> list:
  f, out = "truth_log.yaml", []
  for i, e in enumerate(rows, 1):
    if not isinstance(e, dict) or not DATE.match(str(e.get("date") or "")) or not e.get("note"):
      problems.add(f, i, "-", "each entry needs a date written YYYY-MM-DD and a note")
      continue
    out.append(e)
  return out

def _resolves(ref: dict, known: set) -> bool:
  if ref["mark"] is not None:
    return (ref["sheet"], ref["class"], normal_mark(ref["mark"])) in known
  return (ref["sheet"], ref["class"], "key:" + ref["key"].upper()) in known

def normal_mark(mark) -> str:
  return re.sub(r"[\s\-_]+", "", str(mark)).upper()

def element_keys(elements: list) -> set:
  keys = set()
  for e in elements:
    if e.mark is not None:
      keys.add((e.sheet, e.cls.value, normal_mark(e.mark)))
    if e.attrs.get("key") is not None:
      keys.add((e.sheet, e.cls.value, "key:" + str(e.attrs["key"]).upper()))
  return keys

def is_draft(stamp: TruthStamp | None) -> bool:
  return stamp is not None and (stamp.by is V.TruthSource.DRAFT or str(stamp.source).strip().lower() == DRAFT_SOURCE)

class _NoAlias(yaml.SafeDumper):
  def ignore_aliases(self, data):
    return True

def folder_key(folder: str) -> str:
  return os.path.basename(os.path.normpath(folder))

def _refuse(folder: str, message: str) -> None:
  raise TruthFormatError([{"file": os.path.basename(os.path.normpath(folder)), "row": "-", "field": "folder", "message": message}])

def _document_sha(folder: str, incoming: dict | None) -> str:
  doc = incoming
  if doc is None:
    path = os.path.join(folder, "document.yaml")
    if not os.path.isfile(path):
      _refuse(folder, "has no document.yaml, so the PDF it belongs to is not known; nothing was written")
    with open(path, encoding="utf-8") as fh:
      doc = yaml.safe_load(fh) or {}
  return str(doc.get("sha256") or "") if isinstance(doc, dict) else ""

def check_folder_key(folder: str, incoming_document: dict | None = None) -> None:
  key = folder_key(folder)
  if not re.fullmatch(r"[0-9a-f]{%d}" % KEY_LEN, key):
    _refuse(folder, f"{key} is not the first {KEY_LEN} characters of a PDF's sha256; nothing was written")
  sha = _document_sha(folder, incoming_document)
  if not re.fullmatch(r"[0-9a-f]{64}", sha) or sha[:KEY_LEN] != key:
    _refuse(folder, f"is named {key}, but its document.yaml gives the PDF hash {sha[:KEY_LEN] or 'none'}; nothing was written")

def write_truth_files(folder: str, files: dict, check: bool = True) -> list:
  unknown = [n for n in files if n not in FILES]
  if unknown:
    raise ValueError(f"{', '.join(unknown)} is not a truth file; the truth files are {', '.join(FILES)}")
  incoming_doc = files.get("document.yaml")
  check_folder_key(folder, incoming_doc if isinstance(incoming_doc, dict) else None)
  
  texts = {}
  for name, data in files.items():
    want = dict if name == "document.yaml" else list
    text = data if isinstance(data, str) else yaml.dump(data, Dumper=_NoAlias, sort_keys=False, allow_unicode=True, width=200, default_flow_style=False)
    try:
      parsed = yaml.safe_load(text)
    except yaml.YAMLError as exc:
      raise TruthFormatError([{"file": name, "row": "-", "field": "-", "message": f"what was about to be written is not valid YAML: {str(exc).splitlines()[0]}"}])
    parsed = want() if parsed is None else parsed
    if not isinstance(parsed, want):
      raise TruthFormatError([{"file": name, "row": "-", "field": "-", "message": f"must be a {'mapping' if want is dict else 'list'}"}])
    if not isinstance(data, str) and parsed != data:
      raise TruthFormatError([{"file": name, "row": "-", "field": "-", "message": "does not read back as the rows given; nothing was written"}])
    texts[name] = text if text.endswith("\n") else text + "\n"
    
  if check:
    stage = tempfile.mkdtemp()
    try:
      mirror = os.path.join(stage, folder_key(folder))
      os.makedirs(mirror)
      for name in FILES:
        src = os.path.join(folder, name)
        if name in texts:
          with open(os.path.join(mirror, name), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(texts[name])
        elif os.path.isfile(src):
          shutil.copy2(src, os.path.join(mirror, name))
      if all(os.path.isfile(os.path.join(mirror, n)) for n in FILES):
        load_set(mirror)
    finally:
      shutil.rmtree(stage, ignore_errors=True)
  os.makedirs(folder, exist_ok=True)
  
  tmps = []
  try:
    for name, text in texts.items():
      tmp = os.path.join(folder, name + ".tmp")
      with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
        fh.flush()
        os.fsync(fh.fileno())
      tmps.append((tmp, os.path.join(folder, name)))
      
  except OSError:
    for tmp, _final in tmps:
      if os.path.isfile(tmp):
        os.remove(tmp)
    raise
  for tmp, final in tmps:
    os.replace(tmp, final)
  return sorted(texts)

def load_set(folder: str) -> TruthSet:
  problems = _Problems()
  document = _document(folder, problems)
  pages = document.pages if document else 0
  register = _register(_read(folder, "register.yaml", problems, list), pages, problems)
  elements = _elements(_read(folder, "elements.yaml", problems, list), pages, problems)
  joins = _joins(_read(folder, "joins.yaml", problems, list), pages, problems)
  params = _params(_read(folder, "params.yaml", problems, list), pages, problems)
  log = _log(_read(folder, "truth_log.yaml", problems, list), problems)
  known = element_keys(elements)
  
  for i, j in enumerate(joins, 1):
    for side, ref in (("from", j.src), ("to", j.dst)):
      if not _resolves(ref, known):
        problems.add("joins.yaml", i, side, f"{ref['class']} {ref['mark'] or ref['key']} on page {ref['sheet']} is not in elements.yaml")
  for i, p in enumerate(params, 1):
    if not _resolves(p.element, known):
      problems.add("params.yaml", i, "element", f"{p.element['class']} {p.element['mark'] or p.element['key']} on page {p.element['sheet']} is not in elements.yaml")
  if problems.items:
    raise TruthFormatError(problems.items)
  return TruthSet(folder=folder, document=document, register=register, elements=elements, joins=joins, params=params, log=log)
