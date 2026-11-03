from __future__ import annotations
import os
import yaml
import re
from app.modules.drawings_boq.lab.bill import BillLine, parse_bill, _text, _number
from app.modules.drawings_boq.lab import tolerances as T
from app.modules.drawings_boq.takeoff.proof import case as CASE
from app.modules.drawings_boq.lab.aliases import bill_key

CASE_CLASSES = ("DRAWING", "QS_ERROR", "CONVENTION", "NEEDS_DECISION")
LINE_KINDS = ("MEASURED", "ALLOWANCE", "QS_ERROR")
FORMATS = ("WORKSHEET_MAP", "SUMMARY")
FACT_KINDS = ("COUNT_BY_MARK", "COUNT_BY_LABEL", "MEMBER_SIZE", "LEVEL", "ROOM_SIZE", "AREA", "SLAB_THICKNESS", "BEAM_SIZE", "TANK_SIZE", "ELEC_COUNT",
  "WALL_RUN", "FOOTING_SIZE", "COLUMN_SIZE", "STEP_TABLE")
CASES_DIR_ENV = "TRACE_CASES_DIR"
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cases")

def _yaml(path: str):
  with open(path, encoding="utf-8") as fh:
    return yaml.safe_load(fh)

def load_case(folder: str) -> dict:
  path = os.path.join(folder, "case.yaml")
  if not os.path.isfile(path):
    raise ValueError(f"{folder} has no case.yaml.")
  try:
    raw = _yaml(path) or {}
  except yaml.YAMLError as e:
    raise ValueError(f"{path} is not valid YAML: {e}.")
  if not raw.get("name"):
    raise ValueError(f"{path} has no name.")
  pdfs = raw.get("pdfs") or []

  if not pdfs or not all(isinstance(p, str) and p for p in pdfs):
    raise ValueError(f"{path} lists no PDF.")
  wb = raw.get("workbook") or {}
  if wb and wb.get("format") not in FORMATS:
    raise ValueError(f"{path}: workbook format must be one of {', '.join(FORMATS)}.")
  out = {"name": str(raw["name"]), "tier": str(raw.get("tier") or "C"), "pdfs": [str(p) for p in pdfs], "sha256": dict(raw.get("sha256") or {}), "workbook": wb or None,
    "block_floor": dict(raw.get("block_floor") or {}), "company_rules": raw.get("company_rules"), "note": raw.get("note") or "", "folder": folder}
  out["expected"] = load_expected(os.path.join(folder, "expected.yaml"))
  out["facts"] = load_facts(os.path.join(folder, "facts.yaml"))
  out["decisions"] = load_decisions(folder)
  out["corrections"] = load_corrections(folder)
  fixed = {c["line"] for c in out["corrections"]}
  for e in out["expected"]:
    if e["kind"] == "QS_ERROR" and e["key"] not in fixed:
      raise ValueError(f"{folder}: the line {e['key']} is a QS_ERROR and has no entry in qs_corrections.yaml; a QS error needs evidence and a signature there.")
  out["residuals"] = load_residuals(folder)
  out["conventions"] = load_conventions(folder)
  return out

ANSWERED_BY = ("DRAWING", "QS")
EVIDENCE_KINDS = ("DRAWING", "WORKBOOK")
SIGNERS = ("REHAN_EVIDENCE",)
DRAWING_REF = re.compile(r"\.pdf,? p\.\s*\d+", re.I)

def _list_file(path: str) -> list:
  if not os.path.isfile(path):
    return []
  doc = _yaml(path) or []
  if not isinstance(doc, list):
    raise ValueError(f"{path} must be a list.")
  return doc

def _need(path: str, i: int, e, *names) -> None:
  if not isinstance(e, dict):
    raise ValueError(f"{path}, entry {i + 1}: every entry is a mapping.")
  for n in names:
    if e.get(n) in (None, ""):
      raise ValueError(f"{path}, entry {i + 1}: `{n}` is missing.")

def load_decisions(folder: str) -> list:
  """decisions.yaml: one answer to one open decision, [{id, value, answered_by (DRAWING or QS), date, source}]. `id` is the decision id the score prints under 'Open decisions',
  `value` one of that decision's option values. DRAWING means the answer was read off the drawing by Rehan, QS that the QS gave it."""
  path = os.path.join(folder, "decisions.yaml")
  out, seen = [], set()
  for i, e in enumerate(_list_file(path)):
    _need(path, i, e, "id", "value", "answered_by", "date", "source")
    by = str(e["answered_by"]).upper()
    if by not in ANSWERED_BY:
      raise ValueError(f"{path}, entry {i + 1}: answered_by must be one of {', '.join(ANSWERED_BY)}.")
    if not isinstance(e["id"], str):
      raise ValueError(f"{path}, entry {i + 1}: write the id in quotes ({e['id']!r} was read as a number).")
    value = e["value"]
    if isinstance(value, float) and value.is_integer():
      value = int(value)
    did = e["id"]
    if did in seen:
      raise ValueError(f"{path}: the decision {did} is answered twice.")
    seen.add(did)
    out.append({"id": did, "value": str(value), "answered_by": by, "date": str(e["date"]), "source": str(e["source"])})
  return out

def _evidence(path: str, i: int, e) -> list:
  rows = e.get("evidence")
  if not isinstance(rows, list) or not rows:
    raise ValueError(f"{path}, entry {i + 1} ({e.get('line')}): no evidence. List what shows his figure departs from the drawing as `evidence: [{{kind: DRAWING or WORKBOOK, ref, says}}]`; a correction without it is refused.")
  out = []
  for j, x in enumerate(rows):
    if not isinstance(x, dict) or str(x.get("kind") or "").upper() not in EVIDENCE_KINDS or any(x.get(n) in (None, "") for n in ("ref", "says")):
      raise ValueError(f"{path}, entry {i + 1} ({e.get('line')}), evidence {j + 1}: each piece of evidence is {{kind: {' or '.join(EVIDENCE_KINDS)}, ref, says}}.")
    kind = str(x["kind"]).upper()
    if kind == "DRAWING" and not DRAWING_REF.search(str(x["ref"])):
      raise ValueError(f"{path}, entry {i + 1} ({e.get('line')}), evidence {j + 1}: a DRAWING reference names the PDF and the page, like `Islamabad_Plot_1.pdf p.6`.")
    out.append({"kind": kind, "ref": str(x["ref"]), "says": str(x["says"])})
  return out

def load_corrections(folder: str) -> list:
  """qs_corrections.yaml: a claim that one of his figures departs from the drawing, [{line, qs_figure, corrected, reason, evidence, signed, signed_by}]. It is applied at the `ruled` level only
  when it has evidence and is signed by REHAN_EVIDENCE; the score prints both figures. It is not his agreement."""
  path = os.path.join(folder, "qs_corrections.yaml")
  out, seen = [], set()

  for i, e in enumerate(_list_file(path)):
    _need(path, i, e, "line", "qs_figure", "corrected", "reason")
    evidence = _evidence(path, i, e)
    for n in ("qs_figure", "corrected"):
      if isinstance(e[n], bool) or not isinstance(e[n], (int, float)):
        raise ValueError(f"{path}, entry {i + 1}: {n} must be a number.")
    if not isinstance(e.get("signed"), bool):
      raise ValueError(f"{path}, entry {i + 1}: `signed` must be true or false.")
    if e["signed"] and str(e.get("signed_by") or "").upper() not in SIGNERS:
      raise ValueError(f"{path}, entry {i + 1} ({e['line']}): a signed correction names `signed_by: {SIGNERS[0]}`.")
    if str(e["line"]) in seen:
      raise ValueError(f"{path}: the line {e['line']} is corrected twice.")
    seen.add(str(e["line"]))
    out.append({"line": str(e["line"]), "qs_figure": float(e["qs_figure"]), "corrected": float(e["corrected"]), "reason": str(e["reason"]), "signed": e["signed"], "evidence": evidence,
      "signed_by": str(e["signed_by"]).upper() if e.get("signed_by") else None})
  return out

def load_conventions(folder: str) -> list:
  path = os.path.join(folder, "conventions.yaml")
  out = []
  for i, e in enumerate(_list_file(path)):
    _need(path, i, e, "id", "line", "key", "basis", "qs", "methods")
    if e["basis"] not in ("INFERRED", "STANDARD"):
      raise ValueError(f"{path}, entry {i + 1}: the basis is INFERRED or STANDARD.")
    out.append({"id": str(e["id"]), "question": str(e.get("question") or ""), "key": str(e["key"]), "scope": dict(e.get("scope") or {}), "line": str(e["line"]), "qs": float(e["qs"]), "basis": e["basis"],
      "value": e.get("value"), "margin_pct": e.get("margin_pct"), "methods": list(e["methods"])})
  return out

def load_residuals(folder: str) -> list:
  path = os.path.join(folder, "residuals.yaml")
  out, seen = [], set()
  for i, e in enumerate(_list_file(path)):
    _need(path, i, e, "line", "cause")
    if e.get("pack") in (None, "") and e.get("question") in (None, ""):
      raise ValueError(f"{path}, entry {i + 1}: give the `pack` that will fix {e['line']} or the `question` that is open.")
    if str(e["line"]) in seen:
      raise ValueError(f"{path}: the line {e['line']} is listed twice.")
    seen.add(str(e["line"]))
    out.append({"line": str(e["line"]), "cause": str(e["cause"]), "pack": None if e.get("pack") in (None, "") else str(e["pack"]), "question": None if e.get("question") in (None, "") else str(e["question"])})
  return out

def load_company_rules(case: dict) -> tuple:
  name = case.get("company_rules")
  if not name:
    return [], [], None
  
  from app.engine.measure import rulebook as RB
  path = os.path.join(case["folder"], str(name))
  if not os.path.isfile(path):
    return [], [f"{name} is not in the case folder."], str(name)
  rows, problems = RB.load_rules(path)
  return rows, problems, str(name)

def load_expected(path: str) -> list:
  if not os.path.isfile(path):
    return []

  doc = _yaml(path) or []
  if not isinstance(doc, list):
    raise ValueError(f"{path} must be a list of bill lines.")
  out, seen = [], set()
  for i, e in enumerate(doc):
    if not isinstance(e, dict) or not e.get("key"):
      raise ValueError(f"{path}, entry {i + 1}: every line needs a key.")
    key = str(e["key"])
    if key in seen:
      raise ValueError(f"{path}: the key {key} is used twice.")
    seen.add(key)
    cls = str(e.get("class") or "DRAWING").upper()
    if cls not in CASE_CLASSES:
      raise ValueError(f"{path}, {key}: class must be one of {', '.join(CASE_CLASSES)}.")

    kind = str(e.get("kind") or "MEASURED").upper()
    if kind not in LINE_KINDS:
      raise ValueError(f"{path}, {key}: kind must be one of {', '.join(LINE_KINDS)}.")
    if kind != "MEASURED" and not str(e.get("basis") or "").strip():
      raise ValueError(f"{path}, {key}: a {kind} line says why in `basis` (an allowance is a lump sum, a typed round figure or a figure the QS cannot explain).")
    qs = e.get("qs")
    drawing = e.get("drawing")
    for name, v in (("qs", qs), ("drawing", drawing)):
      if v is not None and (isinstance(v, bool) or not isinstance(v, (int, float))):
        raise ValueError(f"{path}, {key}: {name} must be a number or null.")
    if e.get("faces") not in (None, "ABOVE_GROUND"):
      raise ValueError(f"{path}, {key}: faces is ABOVE_GROUND or left out.")
    
    tol = e.get("tolerance_pct")
    out.append({"key": key, "item": str(e.get("item") or ""), "unit": str(e.get("unit") or ""), "qs": None if qs is None else float(qs), "drawing": None if drawing is None else float(drawing),
      "class": cls, "kind": kind, "basis": str(e.get("basis") or ""), "tolerance_pct": None if tol is None else float(tol), "note": str(e.get("note") or ""), "family": e.get("family"), "families": [str(f) for f in (e.get("families") or [])], "faces": e.get("faces"), "floor": e.get("floor"), "grade": e.get("grade"),
      "match": [str(w).lower() for w in (e.get("match") or [])]})
  return out

def load_facts(path: str) -> list:
  if not os.path.isfile(path):
    return []
  doc = _yaml(path) or []
  if not isinstance(doc, list):
    raise ValueError(f"{path} must be a list of facts.")
  facts = [dict(f) for f in doc if isinstance(f, dict)]
  from app.modules.drawings_boq.takeoff.proof import fact_kinds as FK
  bad = [f"fact {i + 1} ({f.get('kind')} {f.get('mark') or f.get('name') or f.get('section') or ''}): {why}" for i, f in enumerate(facts) for why in FK.source_problems(f)]
  if bad:
    raise ValueError(f"{path}: every fact must cite a drawing PDF and page.\n" + "\n".join(bad))
  return facts

def cases_dir(explicit: str | None = None) -> str | None:
  return explicit or os.environ.get(CASES_DIR_ENV) or None

def find_files(case: dict, files_dir: str | None) -> tuple:
  found, problems = {}, []

  for name in case["pdfs"]:
    p = os.path.join(files_dir, name) if files_dir else None
    if not p or not os.path.isfile(p):
      problems.append(f"{name} is not in {files_dir or 'a folder named by TRACE_CASES_DIR'}.")
      continue

    want = case["sha256"].get(name)
    if want and CASE.sha256_of(p) != want:
      problems.append(f"{name} is not the file this case was made for (its hash differs).")
      continue
    found[name] = p
  return found, problems

def list_cases(root: str = HERE) -> list:
  if not os.path.isdir(root):
    return []
  return sorted(d for d in os.listdir(root) if os.path.isfile(os.path.join(root, d, "case.yaml")))

def _summary_header(ws):
  for r in range(1, 40):
    cells = [_text(ws.cell(r, c).value).lower() for c in range(1, 13)]
    d = next((i for i, x in enumerate(cells) if x.startswith("desc") or x in ("item", "particulars")), None)
    u = next((i for i, x in enumerate(cells) if x.startswith("unit")), None)
    q = next((i for i, x in enumerate(cells) if x.startswith("quant") or x.startswith("qty") or x.startswith("total")), None)
    if d is not None and u is not None and q is not None:
      return r, d + 1, u + 1, q + 1
  return None

def read_summary(data: bytes) -> tuple:
  import io
  import openpyxl
  wb = openpyxl.load_workbook(io.BytesIO(data), data_only=True)
  lines, problems = [], []

  for ws in wb.worksheets:
    head = _summary_header(ws)
    if head is None:
      problems.append(f"Sheet {ws.title}: no header row with description, unit and quantity.")
      continue
    hr, cd, cu, cq = head
    section = ""

    for r in range(hr + 1, ws.max_row + 1):
      item = _text(ws.cell(r, cd).value)
      unit = _text(ws.cell(r, cu).value)
      qty = _number(ws.cell(r, cq).value)
      if not item:
        continue
      if not unit and qty is None:
        section = item
        continue
      if qty is None:
        continue

      lines.append(BillLine(row=r, section=f"{ws.title} / {section}" if len(wb.worksheets) > 1 else section, item=item, unit=unit, quantity=qty))
  return lines, problems

def read_workbook(path: str, fmt: str) -> tuple:
  with open(path, "rb") as fh:
    data = fh.read()
  if fmt == "WORKSHEET_MAP":
    try:
      return list(parse_bill(data).lines), []
    except ValueError as e:
      return [], [f"{os.path.basename(path)}: {e}"]
  return read_summary(data)

def _slug(text: str) -> str:
  return re.sub(r"[^A-Z0-9]+", "_", text.upper()).strip("_")[:40] or "ALL"

def draft_expected(lines, block_floor: dict | None = None) -> tuple:
  entries, left, used = [], [], {}

  for bl in lines:
    fam = bill_key(bl.item)
    if fam is None or fam == "LUMP_SUM":
      left.append({"item": bl.item, "unit": bl.unit, "quantity": bl.quantity, "section": bl.section})
      continue
    block = _slug(bl.section) if bl.section else "ALL"
    floor = (block_floor or {}).get(bl.section)
    base = f"{fam}/{floor or block}"
    n = used.get(base, 0) + 1
    used[base] = n

    key = base if n == 1 else f"{base}/{n}"
    e = {"key": key, "item": bl.item, "unit": bl.unit.lower(), "qs": round(float(bl.quantity), 3), "drawing": round(float(bl.quantity), 3), "class": "DRAWING",
      "tolerance_pct": T.default_for(fam), "note": bl.section.title() if bl.section else "", "family": fam}
    entries.append(e)
  return entries, left

FIELD_ORDER = ("key", "item", "unit", "qs", "drawing", "class", "tolerance_pct", "note", "family", "families", "faces", "floor", "grade", "match")

def dump_expected(entries: list, header: str = "") -> str:
  out = [("# " + h).rstrip() for h in header.splitlines()] if header else []
  for e in entries:
    first = True
    for f in FIELD_ORDER:
      if f not in e or e[f] in ("", [], None) and f not in ("drawing", "qs"):
        continue
      v = e[f]
      text = yaml.safe_dump({f: v}, default_flow_style=True, allow_unicode=True, width=1000).strip()
      text = text[1:-1].strip() if text.startswith("{") else text
      out.append(("- " if first else "  ") + text)
      first = False
  return "\n".join(out) + "\n"
