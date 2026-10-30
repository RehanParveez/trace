from __future__ import annotations
import ast
import importlib
import pathlib
import sys

def _root() -> pathlib.Path:
  import app
  return pathlib.Path(app.__file__).resolve().parent

def _modules(root: pathlib.Path, *parts: str):
  base = root.joinpath(*parts)
  for path in sorted(base.rglob("*.py")):
    if "__pycache__" in path.parts:
      continue
    rel = path.relative_to(root.parent).with_suffix("")
    name = ".".join(rel.parts)
    yield name[: -len(".__init__")] if name.endswith(".__init__") else name

def import_all(root: pathlib.Path) -> list:
  failed = []
  for name in [*_modules(root, "modules", "drawings_boq"), *_modules(root, "engine")]:
    try:
      importlib.import_module(name)
    except Exception as exc:
      failed.append((name, f"{type(exc).__name__}: {str(exc)[:160]}"))
  return failed

def _file_of(root: pathlib.Path, dotted: str) -> pathlib.Path | None:
  parts = dotted.split(".")
  if parts[0] != root.name:
    return None
  base = root.joinpath(*parts[1:])
  if base.with_suffix(".py").is_file():
    return base.with_suffix(".py")
  if (base / "__init__.py").is_file():
    return base / "__init__.py"
  return None

def _top_names(path: pathlib.Path) -> tuple:
  tree = ast.parse(path.read_text(encoding="utf8", errors="replace"))
  names, star = set(), False
  def walk(body):
    nonlocal star
    for node in body:
      if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        names.add(node.name)
      elif isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        for t in targets:
          for n in ast.walk(t):
            if isinstance(n, ast.Name):
              names.add(n.id)

      elif isinstance(node, ast.Import):
        for a in node.names:
          names.add((a.asname or a.name).split(".")[0])
      elif isinstance(node, ast.ImportFrom):
        for a in node.names:
          if a.name == "*":
            star = True
          else:
            names.add(a.asname or a.name)

      elif isinstance(node, (ast.If, ast.Try, ast.With)):
        walk(getattr(node, "body", []))
        walk(getattr(node, "orelse", []))
        for h in getattr(node, "handlers", []):
          walk(h.body)
        walk(getattr(node, "finalbody", []))

  walk(tree.body)
  return names, star

def lazy_imports(root: pathlib.Path) -> list:
  misses, cache = [], {}
  for path in sorted(root.rglob("*.py")):
    if "__pycache__" in path.parts:
      continue
    try:
      tree = ast.parse(path.read_text(encoding="utf8", errors="replace"))
    except SyntaxError as exc:
      misses.append((str(path.relative_to(root.parent)), exc.lineno or 0, "syntax", f"SyntaxError: {exc.msg}"))
      continue

    for fn in ast.walk(tree):
      if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
        continue
      for node in ast.walk(fn):
        if not isinstance(node, ast.ImportFrom) or node.level or not (node.module or "").startswith(root.name + "."):
          continue
        where = (str(path.relative_to(root.parent)), node.lineno)
        target = _file_of(root, node.module)
        
        if target is None:
          misses.append((*where, f"from {node.module} import ...", "module not found"))
          continue
        for a in node.names:
          if a.name == "*":
            continue
          if target not in cache:
            cache[target] = _top_names(target)
          names, star = cache[target]
          if a.name in names or star or (target.name == "__init__.py" and _file_of(root, f"{node.module}.{a.name}")):
            continue
          if _file_of(root, f"{node.module}.{a.name}") is not None:
            continue
          misses.append((*where, f"from {node.module} import {a.name}", "name not found"))
  return misses

KNOWN = {
  ("app/engine/measure/member_steel.py", "lap_of"): "two identical copies; Pack 195 removes one",
}
USELESS = (ast.Name, ast.Subscript, ast.Attribute, ast.Compare, ast.BinOp, ast.BoolOp, ast.UnaryOp, ast.Tuple, ast.List, ast.Dict, ast.Set, ast.JoinedStr)
EXEMPT_DECORATORS = ("setter", "getter", "deleter", "overload", "register")

def _sources(root: pathlib.Path):
  for sub in ("modules/drawings_boq", "engine"):
    for path in sorted(root.joinpath(*sub.split("/")).rglob("*.py")):
      if "__pycache__" not in path.parts:
        yield path, str(path.relative_to(root.parent)).replace("\\", "/")

def undefined_names(root: pathlib.Path) -> list:
  try:
    from pyflakes import checker, messages
  except ImportError:
    return [("-", 0, "pyflakes is not installed (pip install pyflakes)")]
  bad = (messages.UndefinedName, messages.UndefinedLocal, messages.UndefinedExport)
  out = []
  for path, rel in _sources(root):
    try:
      tree = ast.parse(path.read_text(encoding="utf8", errors="replace"))
    except SyntaxError as exc:
      out.append((rel, exc.lineno or 0, f"SyntaxError: {exc.msg}"))
      continue
    out += [(rel, m.lineno, m.message % m.message_args) for m in checker.Checker(tree, filename=rel).messages if isinstance(m, bad)]
  return out

def _decorated_as_variant(node) -> bool:
  for d in getattr(node, "decorator_list", []):
    target = d.func if isinstance(d, ast.Call) else d
    name = target.attr if isinstance(target, ast.Attribute) else getattr(target, "id", "")
    if name in EXEMPT_DECORATORS:
      return True
  return False

def structure_problems(root: pathlib.Path) -> list:
  """Code that cannot be what was meant: a function or class defined twice in one block (the first copy never runs), a statement after a return, raise, continue or break,
  and an expression statement that does nothing (a stray name or subscript). [(file, line, kind, text)]; the KNOWN ones are marked and do not fail the check."""
  out = []
  for path, rel in _sources(root):
    try:
      tree = ast.parse(path.read_text(encoding="utf8", errors="replace"))
    except SyntaxError:
      continue
    for parent in ast.walk(tree):
      for field in ("body", "orelse", "finalbody"):
        stmts = getattr(parent, field, None)
        if not isinstance(stmts, list) or not stmts or not isinstance(stmts[0], ast.stmt):
          continue
        seen: dict = {}
        for i, st in enumerate(stmts):
          if isinstance(st, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if st.name in seen and not _decorated_as_variant(st):
              out.append((rel, st.lineno, "DUPLICATE DEF", f"{st.name} is also defined at line {seen[st.name]}; only the last copy is used", (rel.removeprefix("backend/"), st.name) in KNOWN))
            seen.setdefault(st.name, st.lineno)
          if isinstance(st, (ast.Return, ast.Raise, ast.Continue, ast.Break)) and i + 1 < len(stmts):
            out.append((rel, stmts[i + 1].lineno, "UNREACHABLE", f"statement after the {type(st).__name__.lower()} at line {st.lineno} never runs", False))
          if isinstance(st, ast.Expr) and isinstance(st.value, USELESS) and not any(isinstance(n, (ast.Call, ast.Await, ast.Yield, ast.YieldFrom, ast.NamedExpr)) for n in ast.walk(st.value)):
            out.append((rel, st.lineno, "USELESS EXPRESSION", "a statement that only names a value and does nothing with it", False))
  return sorted(out)

def missing_attributes(root: pathlib.Path) -> list:
  out, seen, cache = [], set(), {}
  def mod(name):
    if name not in cache:
      try:
        cache[name] = importlib.import_module(name)
      except Exception:
        cache[name] = None
    return cache[name]
  
  for path, rel in _sources(root):
    try:
      tree = ast.parse(path.read_text(encoding="utf8", errors="replace"))
    except SyntaxError:
      continue
    alias = {}
    
    for n in ast.walk(tree):
      if isinstance(n, ast.ImportFrom) and n.module and n.module.startswith(root.name + ".") and not n.level:
        for a in n.names:
          m = mod(f"{n.module}.{a.name}")
          if m is not None and hasattr(m, "__file__"):
            alias[a.asname or a.name] = m
    for n in ast.walk(tree):
      if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id in alias and not hasattr(alias[n.value.id], n.attr) and (rel, n.value.id, n.attr) not in seen:
        seen.add((rel, n.value.id, n.attr))
        out.append((rel, n.lineno, f"{n.value.id}.{n.attr}", alias[n.value.id].__name__))
  return out

def scope_check() -> list:
  from app.modules.drawings_boq.takeoff.extract import config as C
  from app.modules.drawings_boq.takeoff.extract import note_scope as NS
  from app.modules.drawings_boq.takeoff.extract import safe as SF
  from app.modules.drawings_boq.takeoff.model import members as MB
  out = [(k, "has no scope in extract.note_scope") for k in sorted(set(C.NOTES) - set(NS.SCOPE))]
  out += [(k, "is in extract.note_scope but not in config.NOTES") for k in sorted(set(NS.SCOPE) - set(C.NOTES))]
  out += [(k, f"has the scope {v!r}") for k, v in sorted(NS.SCOPE.items()) if v not in (NS.ROW, NS.SHEET, NS.DRAWING)]
  return out

def seed_check() -> list:
  from app.engine.measure import rulebook
  return rulebook.seed_problems()

def main() -> int:
  root = _root()
  failed = import_all(root)
  misses = lazy_imports(root)
  seed = seed_check()
  scopes = scope_check()
  undefined = undefined_names(root)
  structure = structure_problems(root)
  attrs = missing_attributes(root)
  for file, line, text in undefined:
    print(f"UNDEFINED NAME {file}:{line}  {text}")
  for file, line, kind, text, known in structure:
    print(f"{kind:14} {file}:{line}  {text}" + ("  (known, left for a later pack)" if known else ""))
  for file, line, ref, module in attrs:
    print(f"MODULE ATTR    {file}:{line}  {ref}  (no such name in {module})")
  for key, what in scope_check():
    print(f"NOTE SCOPE     {key}: {what}")
  for key, what in seed:
    print(f"RULE SEED      {key}: {what}")
  for name, err in failed:
    print(f"IMPORT FAILS   {name}: {err}")
  for file, line, text, why in misses:
    print(f"LAZY IMPORT    {file}:{line}  {text}  ({why})")
  print(f"{len(failed)} module(s) fail to import, {len(misses)} in-function import(s) do not resolve, {len(seed)} seed figure(s) differ from the code, {len(scopes)} note code(s) without a valid scope, {len(undefined)} undefined name(s), {len([x for x in structure if not x[4]])} structure problem(s), {len(attrs)} module attribute(s) that do not exist.")
  return 1 if failed or misses or seed or scopes or undefined or attrs or any(not x[4] for x in structure) else 0

if __name__ == "__main__":
  sys.exit(main())
