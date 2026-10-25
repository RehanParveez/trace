from __future__ import annotations
from pathlib import Path
import ast
from functools import lru_cache

ROOT = Path(__file__).resolve().parents[5]
SCAN = ROOT / "app" / "modules" / "drawings_boq"
MAX_LISTED = 40

def _module_file(dotted: str) -> Path | None:
  base = ROOT.joinpath(*dotted.split("."))
  if base.with_suffix(".py").is_file():
    return base.with_suffix(".py")
  if (base / "__init__.py").is_file():
    return base / "__init__.py"
  return None

def _is_package(dotted: str) -> bool:
  return (ROOT.joinpath(*dotted.split(".")) / "__init__.py").is_file()

@lru_cache(maxsize=None)
def _top_names(path: Path) -> frozenset | None:
  try:
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
  except (OSError, SyntaxError, ValueError):
    return None
  names: set = set()
  def targets(node):
    if isinstance(node, ast.Name):
      names.add(node.id)
    elif isinstance(node, (ast.Tuple, ast.List)):
      for e in node.elts:
        targets(e)

  def walk(body):
    for node in body:
      if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        names.add(node.name)
      elif isinstance(node, ast.Assign):
        for t in node.targets:
          targets(t)
      elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
        targets(node.target)
      elif isinstance(node, (ast.Import, ast.ImportFrom)):
        for a in node.names:
          if a.name == "*":
            names.add("*")
          names.add((a.asname or a.name).split(".")[0])

      elif isinstance(node, (ast.If, ast.Try)):
        walk(node.body)
        walk(getattr(node, "orelse", []))
        for h in getattr(node, "handlers", []):
          walk(h.body)
        walk(getattr(node, "finalbody", []))
      elif isinstance(node, (ast.With, ast.For, ast.While)):
        walk(node.body)
  walk(tree.body)
  if "*" in names or "__getattr__" in names:
    return None
  return frozenset(names)

def _scan_file(path: Path) -> list:
  try:
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
  except (OSError, SyntaxError, ValueError):
    return []
  aliases: dict = {}
  
  for node in ast.walk(tree):
    if isinstance(node, ast.ImportFrom) and node.module and not node.level:
      for a in node.names:
        dotted = f"{node.module}.{a.name}"
        if a.name != "*" and _module_file(dotted) is not None:
          aliases[a.asname or a.name] = dotted
    elif isinstance(node, ast.Import):
      for a in node.names:
        if a.asname and _module_file(a.name) is not None:
          aliases[a.asname] = a.name
  if not aliases:
    return []
  found: list = []

  for node in ast.walk(tree):
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id in aliases and isinstance(node.ctx, ast.Load):
      dotted = aliases[node.value.id]
      target = _module_file(dotted)
      names = _top_names(target) if target is not None else None
      if names is None or node.attr in names:
        continue
      if _is_package(dotted) and _module_file(f"{dotted}.{node.attr}") is not None:
        continue
      found.append({"file": str(path.relative_to(ROOT)).replace("\\", "/"), "line": node.lineno, "alias": node.value.id, "module": dotted, "name": node.attr})
  return found

@lru_cache(maxsize=1)
def scan() -> dict:
  found: list = []
  files = 0
  for path in sorted(SCAN.rglob("*.py")):
    if "__pycache__" in path.parts:
      continue
    files += 1
    found.extend(_scan_file(path))
  return {"files": files, "unresolved": len(found), "listed": found[:MAX_LISTED]}
