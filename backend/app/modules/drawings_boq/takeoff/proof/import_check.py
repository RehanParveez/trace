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
  for key, what in scope_check():
    print(f"NOTE SCOPE     {key}: {what}")
  for key, what in seed:
    print(f"RULE SEED      {key}: {what}")
  for name, err in failed:
    print(f"IMPORT FAILS   {name}: {err}")
  for file, line, text, why in misses:
    print(f"LAZY IMPORT    {file}:{line}  {text}  ({why})")
  print(f"{len(failed)} module(s) fail to import, {len(misses)} in-function import(s) do not resolve, {len(seed)} seed figure(s) differ from the code, {len(scopes)} note code(s) without a valid scope.")
  return 1 if failed or misses or seed or scopes else 0

if __name__ == "__main__":
  sys.exit(main())
