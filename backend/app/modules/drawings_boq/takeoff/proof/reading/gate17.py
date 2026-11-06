from __future__ import annotations
import argparse
import ast
import io
import os
import pathlib
import re
import sys
import tokenize
import yaml
from app.engine.measure import rule_registry as RR

HERE = pathlib.Path(__file__).resolve().parent
APP = HERE.parents[3]
CASES = HERE / "cases"
ALLOW = HERE / "gate17_allow.yaml"
ROOT = APP.parent.parent
PROOF_PREFIX = "modules/drawings_boq/takeoff/proof/"
CODE_SUFFIXES = (".py",)
DATA_SUFFIXES = (".yaml", ".yml")
SKIP_DIRS = ("__pycache__", ".git", "node_modules")
PAGE_NAMES = ("page", "page_no", "page_num", "page_number", "page_index", "pno", "page_idx")
CASE_KINDS = ("CASE_NAME", "SHEET_MARK", "PAGE_COMPARE", "PROOF_IMPORT", "CASE_SWITCH", "REGISTRY", "CONVENTION_CONSTANT")
CONVENTION_MODULES = ("engine/measure/readings.py", "engine/measure/derived.py")
MIN_REASON_WORDS = 3
MARK_MIN_LEN = 2

def _yaml(path) -> object:
  with open(path, encoding="utf-8") as fh:
    return yaml.safe_load(fh)

def case_names() -> set:
  names: set = set()
  if not CASES.is_dir():
    return names
  for folder in sorted(CASES.iterdir()):
    path = folder / "case.yaml"
    if not path.is_file():
      continue
    raw = _yaml(path) or {}
    base = [folder.name, str(raw.get("name") or "")]
    for pdf in raw.get("pdfs") or []:
      stem = re.sub(r"\.pdf$", "", str(pdf), flags=re.I)
      base.append(stem)
      
    for b in base:
      if len(b) < 4:
        continue
      names.add(b)
      names.add(re.sub(r"[-_ ]+", "", b))
      names.add(re.sub(r"[-_ ]+", "-", b))
      names.add(re.sub(r"[-_ ]+", "_", b))
      names.add(re.sub(r"(?<=[A-Za-z])(?=\d)|(?<=\d)(?=[A-Za-z])", "-", b))
      names.add(re.sub(r"(?<=[A-Za-z])(?=\d)|(?<=\d)(?=[A-Za-z])", "_", b))
  return {n for n in names if len(n) >= 4}

def name_pattern(names: set):
  if not names:
    return None
  body = "|".join(re.escape(n) for n in sorted(names, key=len, reverse=True))
  return re.compile(r"(?<![A-Za-z0-9])(?:" + body + r")(?![A-Za-z0-9])", re.I)

def truth_marks() -> set:
  out: set = set()
  if not CASES.is_dir():
    return out
  for path in CASES.glob("*/reading/*/register.yaml"):
    for row in _yaml(path) or []:
      v = (row or {}).get("sheet_no")
      if v:
        out.add(str(v).strip())
        
  for path in CASES.glob("*/reading/*/elements.yaml"):
    for row in _yaml(path) or []:
      v = (row or {}).get("mark")
      if v:
        out.add(str(v).strip())
  return {m for m in out if len(m) >= MARK_MIN_LEN and any(ch.isdigit() for ch in m) and not re.fullmatch(r"\d+", m)}

def _files(root: pathlib.Path, suffixes: tuple):
  for folder, dirs, names in os.walk(root):
    dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
    for n in sorted(names):
      if n.endswith(suffixes):
        yield pathlib.Path(folder) / n

def _rel(path: pathlib.Path) -> str:
  return path.relative_to(ROOT).as_posix()

def _outside_proof(path: pathlib.Path) -> bool:
  return not path.relative_to(APP).as_posix().startswith(PROOF_PREFIX)

def _docstring_lines(tree: ast.AST) -> set:
  lines: set = set()
  for node in ast.walk(tree):
    if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.body:
      first = node.body[0]
      if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
        lines.update(range(first.lineno, (first.end_lineno or first.lineno) + 1))
  return lines

def _name_of(node: ast.AST) -> str | None:
  if isinstance(node, ast.Name):
    return node.id
  if isinstance(node, ast.Attribute):
    return node.attr
  if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str):
    return node.slice.value
  return None

def scan_python(path: pathlib.Path, names, marks: set) -> list:
  text = path.read_text(encoding="utf-8", errors="replace")
  hits: list = []
  rel = _rel(path)
  try:
    tree = ast.parse(text)
  except SyntaxError:
    return hits
  doc_lines = _docstring_lines(tree)
  lines = text.splitlines()
  if names is not None:
    try:
      for tok in tokenize.generate_tokens(io.StringIO(text).readline):
        if tok.type in (tokenize.STRING, tokenize.COMMENT):
          for m in names.finditer(tok.string):
            ln = tok.start[0] + tok.string[:m.start()].count("\n")
            hits.append({"path": rel, "line": ln, "kind": "CASE_NAME", "text": lines[ln - 1].strip()[:160] if ln <= len(lines) else m.group(0)})
    except tokenize.TokenError:
      pass
  for node in ast.walk(tree):
    if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.lineno not in doc_lines:
      v = node.value.strip()
      if v in marks and not re.search(r"[\\^$*+?()\[\]{}|]", v):
        hits.append({"path": rel, "line": node.lineno, "kind": "SHEET_MARK", "text": lines[node.lineno - 1].strip()[:160]})
    if isinstance(node, ast.Compare):
      sides = [node.left, *node.comparators]
      named = [_name_of(s) for s in sides]
      const = [s for s in sides if isinstance(s, (ast.Constant, ast.Tuple, ast.List, ast.Set)) and (not isinstance(s, ast.Constant) or isinstance(s.value, int) and not isinstance(s.value, bool))]
      if any(n in PAGE_NAMES for n in named) and const and all(isinstance(op, (ast.Eq, ast.NotEq, ast.In, ast.NotIn)) for op in node.ops):
        elts = [e for c in const for e in (c.elts if isinstance(c, (ast.Tuple, ast.List, ast.Set)) else [c])]
        if elts and all(isinstance(e, ast.Constant) and isinstance(e.value, int) and not isinstance(e.value, bool) for e in elts):
          hits.append({"path": rel, "line": node.lineno, "kind": "PAGE_COMPARE", "text": lines[node.lineno - 1].strip()[:160]})
    if isinstance(node, (ast.Import, ast.ImportFrom)):
      mods = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""]
      if any(".takeoff.proof" in m or m.endswith("takeoff.proof") for m in mods):
        hits.append({"path": rel, "line": node.lineno, "kind": "PROOF_IMPORT", "text": lines[node.lineno - 1].strip()[:160]})
  return hits

def scan_data(path: pathlib.Path, names) -> list:
  if names is None:
    return []
  hits: list = []
  rel = _rel(path)
  for i, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
    if names.search(line):
      hits.append({"path": rel, "line": i, "kind": "CASE_NAME", "text": line.strip()[:160]})
  return hits

def case_switch_hits() -> list:
  """A case folder may hold answers (decisions, storeys, sections, corrections, truth) and a proof-only override file, never a file or key that turns a reader on."""
  hits: list = []
  if not CASES.is_dir():
    return hits
  ids = [r["id"] for r in RR.load()]
  for folder in sorted(CASES.iterdir()):
    if not folder.is_dir():
      continue
    for path in sorted(folder.iterdir()):
      if path.name in RR.RETIRED_CASE_FILES:
        hits.append({"path": _rel(path), "line": 1, "kind": "CASE_SWITCH", "text": f"{path.name} switches a reader on for a case; the switch belongs to the registry"})
        continue
      if path.suffix not in DATA_SUFFIXES or path.name == RR.OVERRIDES_FILE:
        continue
      for i, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        for rid in ids:
          if re.search(r"(?<![A-Z0-9_])" + re.escape(rid) + r"(?![A-Z0-9_])", line) and not line.lstrip().startswith("#"):
            hits.append({"path": _rel(path), "line": i, "kind": "CASE_SWITCH", "text": f"{rid} is a registry rule; a case file cannot name it outside {RR.OVERRIDES_FILE}"})
  return hits

def registry_hits() -> list:
  out = [{"path": "backend/app/engine/measure/rule_registry.yaml", "line": 1, "kind": "REGISTRY", "text": p} for p in RR.problems(RR.load())]
  by_id = {r["id"]: r for r in RR.load()}
  for rid, r in sorted(by_id.items()):
    if r.get("status") == "RETIRED":
      continue
    module = next((c for c in (ROOT / r["module"], APP / r["module"], APP / "modules" / "drawings_boq" / r["module"]) if c.is_file()), None)
    text = module.read_text(encoding="utf-8", errors="replace") if module else ""
    if rid not in text:
      out.append({"path": "backend/app/engine/measure/rule_registry.yaml", "line": 1, "kind": "REGISTRY", "text": f"{rid}: the module {r['module']} does not name the rule, so nothing consults the registry for it"})
  return out

def convention_hits() -> list:
  from app.engine.catalogue import conventions as CV
  keys = {c["engine_key"]: c["id"] for c in CV.conventions() if c.get("engine_key")}
  out = []
  
  for rel in CONVENTION_MODULES:
    path = APP / rel
    if not path.is_file():
      continue
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
      if not isinstance(node, ast.Dict):
        continue
      for k, v in zip(node.keys, node.values):
        if isinstance(k, ast.Constant) and k.value in keys:
          val = v.elts[0] if isinstance(v, ast.Tuple) and v.elts else v
          if isinstance(val, ast.Constant) and isinstance(val.value, (int, float)) and not isinstance(val.value, bool):
            out.append({"path": f"backend/app/{rel}", "line": k.lineno, "kind": "CONVENTION_CONSTANT", "text": f"{k.value} is written as {val.value}; its value is held by {keys[k.value]} in conventions_pk.yaml, so read it from there"})
  return out

def load_allow() -> tuple:
  if not ALLOW.is_file():
    return [], []
  raw = _yaml(ALLOW) or []
  problems, entries = [], []
  names = name_pattern(case_names())
  for i, e in enumerate(raw, 1):
    if not isinstance(e, dict) or not all(e.get(k) for k in ("path", "pattern", "reason", "pack")):
      problems.append(f"gate17_allow.yaml entry {i} needs path, pattern, reason and pack")
      continue
    reason = str(e["reason"])
    if len(reason.split()) < MIN_REASON_WORDS or (names and names.search(reason)):
      problems.append(f"gate17_allow.yaml entry {i} ({e['path']}): the reason must say why the pattern is a convention word, in {MIN_REASON_WORDS} or more words, and must not name a case")
      continue
    try:
      entries.append({**e, "re": re.compile(str(e["pattern"]))})
    except re.error as exc:
      problems.append(f"gate17_allow.yaml entry {i}: pattern is not a regular expression: {exc}")
  return entries, problems

def allowed(hit: dict, entries: list) -> dict | None:
  for e in entries:
    if e["path"] == hit["path"] and e["re"].search(hit["text"]):
      return e
  return None

def scan() -> dict:
  names = name_pattern(case_names())
  marks = truth_marks()
  hits: list = []
  for path in _files(APP, CODE_SUFFIXES):
    if _outside_proof(path):
      hits.extend(scan_python(path, names, marks))
  for path in _files(APP, DATA_SUFFIXES):
    if _outside_proof(path):
      hits.extend(scan_data(path, names))
  hits.extend(case_switch_hits())
  hits.extend(registry_hits())
  hits.extend(convention_hits())
  entries, problems = load_allow()
  
  open_hits, kept = [], []
  unique: dict = {}
  for h in hits:
    unique.setdefault((h["path"], h["line"], h["kind"], h["text"]), h)
  for h in unique.values():
    e = allowed(h, entries) if h["kind"] not in ("REGISTRY", "CASE_SWITCH", "CONVENTION_CONSTANT") else None
    (kept if e else open_hits).append({**h, "reason": e["reason"]} if e else h)
  used = {id(allowed(h, entries)) for h in kept}
  stale = [f"gate17_allow.yaml: {e['path']} pattern {e['pattern']!r} matches nothing" for e in entries if id(e) not in used]
  return {"hits": open_hits, "allowed": kept, "problems": problems + stale, "names": len(case_names()), "marks": len(marks), "files": sum(1 for _ in _files(APP, CODE_SUFFIXES + DATA_SUFFIXES))}

def gate() -> tuple:
  res = scan()
  lines = [f"{h['kind']:<12} {h['path']}:{h['line']}  {h['text']}" for h in res["hits"]] + res["problems"]
  ok = not lines
  note = f"no case literal outside takeoff/proof and no convention written twice ({res['files']} files, {res['names']} case names, {res['marks']} truth marks; {len(res['allowed'])} allowed)" if ok else f"{len(res['hits'])} hit(s), {len(res['problems'])} allowlist problem(s)"
  return ok, note, lines

def main(argv: list | None = None) -> int:
  ap = argparse.ArgumentParser(description="Gate 17: no case name, set file name, case sheet number or mark, page-number comparison, proof import or case switch outside takeoff/proof.")
  ap.add_argument("--list", action="store_true", help="also list the allowed hits with their reasons")
  args = ap.parse_args(argv)
  res = scan()
  ok, note, lines = gate()
  print(f"{'ok  ' if ok else 'FAIL'}  gate 17: {note}")
  for ln in lines:
    print(f"      {ln}")
  if args.list:
    for h in res["allowed"]:
      print(f"      allowed  {h['kind']:<12} {h['path']}:{h['line']}  {h['reason']}")
  return 0 if ok else 1

if __name__ == "__main__":
  sys.exit(main())
