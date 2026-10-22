from __future__ import annotations
import pathlib
from dataclasses import dataclass
import ast
import functools

DOTTED = {"C": "app.modules.drawings_boq.takeoff.extract.config", "SG": "app.modules.drawings_boq.takeoff.extract.scalegate"}
CACHE_NAMES = {"lru_cache", "cache", "cached_property"}
ROOT = pathlib.Path(__file__).resolve().parents[2]            
APP_ROOT = ROOT.parents[2]                                   
SKIP_DIRS = {"__pycache__", "tuning"}

CALL_TIME, IMPORT_TIME, BY_NAME, CACHED = "CALL_TIME", "IMPORT_TIME", "BY_NAME", "CACHED"

@dataclass(frozen=True)
class Use:
  file: str           
  line: int
  where: str        
  how: str             
  copy_to: str = ""  

def dotted_name(path: pathlib.Path) -> str:
  parts = list(path.resolve().relative_to(APP_ROOT).with_suffix("").parts)
  if parts and parts[-1] == "__init__":
    parts = parts[:-1]
  return ".".join(parts)

def _absolute(module: str | None, level: int, here: str, is_pkg: bool) -> str:
  if level == 0:
    return module or ""
  base = here.split(".") if is_pkg else here.split(".")[:-1]
  base = base[: len(base) - (level - 1)] if level > 1 else base
  return ".".join([*base, *( [module] if module else [])])

class _Scan(ast.NodeVisitor):
  def __init__(self, rel: str, here: str, is_pkg: bool, own: str | None):
    self.rel, self.here, self.is_pkg, self.own = rel, here, is_pkg, own
    self.aliases: dict = {}            
    self.names: dict = {}             
    self.stack: list = []             
    self.found: list = []             
    self.module_names: set = set()
    self.imports: list = []           
    self._copy: tuple | None = None    

  def visit_Import(self, node):
    for a in node.names:
      for key, dotted in DOTTED.items():
        if a.name == dotted and a.asname:
          self.aliases[a.asname] = key

  def visit_ImportFrom(self, node):
    mod = _absolute(node.module, node.level, self.here, self.is_pkg)
    for a in node.names:
      self.imports.append((mod, a.name))
      local = a.asname or a.name
      for key, dotted in DOTTED.items():
        if f"{mod}.{a.name}" == dotted:
          self.aliases[local] = key
        elif mod == dotted and a.name != "*":
          self.names[local] = (key, a.name)
          self.found.append((key, a.name, Use(self.rel, node.lineno, "", BY_NAME)))

  def _how(self) -> str:
    if not self.stack:
      return IMPORT_TIME
    return CACHED if any(c for _, c in self.stack) else CALL_TIME

  def _where(self) -> str:
    return ".".join(q for q, _ in self.stack)

  def _func(self, node):
    for d in node.decorator_list:
      self.visit(d)
    for d in [*node.args.defaults, *[k for k in node.args.kw_defaults if k is not None]]:
      self.visit(d)
    cached = any((isinstance(d, ast.Name) and d.id in CACHE_NAMES) or (isinstance(d, ast.Attribute) and d.attr in CACHE_NAMES)
      or (isinstance(d, ast.Call) and ((isinstance(d.func, ast.Name) and d.func.id in CACHE_NAMES) or (isinstance(d.func, ast.Attribute) and d.func.attr in CACHE_NAMES)))
      for d in node.decorator_list)
    self.stack.append((node.name, cached))
    for s in node.body:
      self.visit(s)
    self.stack.pop()

  visit_FunctionDef = visit_AsyncFunctionDef = _func

  def visit_Lambda(self, node):
    for d in [*node.args.defaults, *[k for k in node.args.kw_defaults if k is not None]]:
      self.visit(d)
    self.stack.append(("<lambda>", False))
    self.visit(node.body)
    self.stack.pop()

  def visit_ClassDef(self, node):
    for d in [*node.decorator_list, *node.bases]:
      self.visit(d)
    outer, self.stack = self.stack, []                   
    for s in node.body:
      self.visit(s)
    self.stack = outer

  def visit_Assign(self, node):
    if not self.stack and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and isinstance(node.value, (ast.Attribute, ast.Name)):
      self._copy = (node.value, node.targets[0].id)
    self.generic_visit(node)
    self._copy = None

  def _use(self, node) -> Use:
    how = self._how()
    copy = self._copy[1] if (self._copy and self._copy[0] is node and how == IMPORT_TIME) else ""
    return Use(self.rel, node.lineno, self._where(), how, copy)

  def visit_Attribute(self, node):
    if isinstance(node.value, ast.Name) and node.value.id in self.aliases and isinstance(node.ctx, ast.Load):
      self.found.append((self.aliases[node.value.id], node.attr, self._use(node)))
    self.generic_visit(node)

  def visit_Name(self, node):
    if isinstance(node.ctx, ast.Load):
      if self.own and node.id in self.module_names:
        self.found.append((self.own, node.id, self._use(node)))
      elif node.id in self.names and self.stack:
        key, attr = self.names[node.id]
        self.found.append((key, attr, Use(self.rel, node.lineno, self._where(), BY_NAME)))

def _module_level_names(tree: ast.Module) -> set:
  out: set = set()
  for s in tree.body:
    targets = s.targets if isinstance(s, ast.Assign) else [s.target] if isinstance(s, (ast.AnnAssign, ast.AugAssign)) else []
    for t in targets:
      if isinstance(t, ast.Name):
        out.add(t.id)
  return out

def scan_source(source: str, rel: str, here: str, is_pkg: bool = False, own: str | None = None, imports: list | None = None) -> list:
  tree = ast.parse(source)
  s = _Scan(rel, here, is_pkg, own)
  if own:
    s.module_names = _module_level_names(tree)
  s.visit(tree)
  if imports is not None:
    imports.extend((m, n, rel) for m, n in s.imports)
  return s.found

@functools.lru_cache(maxsize=4)
def _scan(root: str) -> tuple:
  base = pathlib.Path(root)
  out: dict = {}
  imports: list = []
  for path in sorted(base.rglob("*.py")):
    if SKIP_DIRS & set(path.relative_to(base).parts):
      continue
  
    here = dotted_name(path)
    own = next((k for k, d in DOTTED.items() if here == d), None)
    for key, name, use in scan_source(path.read_text(encoding="utf-8-sig"), path.relative_to(base).as_posix(), here, path.name == "__init__.py", own, imports):
      out.setdefault((key, name), []).append(use)
  for v in out.values():
    v.sort(key=lambda u: (u.file, u.line))
  return out, tuple(imports)

def scan_package(root: str = str(ROOT)) -> dict:
  return _scan(root)[0]

def imported_by_name(root: str = str(ROOT)) -> set:
  return {(m, n) for m, n, _ in _scan(root)[1]}

def uses_of(key: str, name: str, root: str = str(ROOT)) -> list:
  return list(scan_package(root).get((key, name), []))

def module_of(file: str) -> str:
  return "app.modules.drawings_boq." + file[:-3].replace("/", ".").removesuffix(".__init__")

def linked_copies(uses: list) -> list:
  return [(module_of(u.file), u.copy_to) for u in uses if u.how == IMPORT_TIME and u.copy_to]

def sweep_blockers(uses: list, imported: set | None = None) -> list:
  out = []
  by = {}
  
  for u in uses:
    by.setdefault(u.how, []).append(u)
  if BY_NAME in by:
    out.append(f"imported by name in {_files(by[BY_NAME])}, which keeps the old value")
  frozen = [u for u in by.get(IMPORT_TIME, []) if not u.copy_to or (imported is not None and (module_of(u.file), u.copy_to) in imported)]
  if frozen:
    out.append(f"read when the module loads in {_files(frozen)}, so a new value would not reach it")
  if CACHED in by:
    out.append(f"read inside a cached function in {_files(by[CACHED])}")
  if not uses:
    out.append("nothing in the package reads it")
  return out

def _files(uses: list) -> str:
  return ", ".join(sorted({f"{u.file}:{u.line}" for u in uses})[:3])

def numeric_constants(root: str = str(ROOT), folders: tuple = ("takeoff/extract", "takeoff/prep")) -> dict:
  base = pathlib.Path(root)
  out: dict = {}
  
  for folder in folders:
    for path in sorted((base / folder).glob("*.py")):
      if here_is_config(path):
        continue
      tree = ast.parse(path.read_text(encoding="utf-8-sig"))
      
      rows = []
      for s in tree.body:
        if isinstance(s, ast.Assign) and len(s.targets) == 1 and isinstance(s.targets[0], ast.Name) and s.targets[0].id.isupper():
          v = s.value
          neg = isinstance(v, ast.UnaryOp) and isinstance(v.op, ast.USub)
          v = v.operand if neg else v
          if isinstance(v, ast.Constant) and isinstance(v.value, (int, float)) and not isinstance(v.value, bool):
            rows.append((s.targets[0].id, -v.value if neg else v.value, s.lineno))
      if rows:
        out[path.relative_to(base).as_posix()] = rows
  return out

def here_is_config(path: pathlib.Path) -> bool:
  return path.name in ("config.py", "scalegate.py")
