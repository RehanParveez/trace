from __future__ import annotations
import argparse
import hashlib
import os
import pathlib
import re
import subprocess
import sys

APPLIED, TO_APPLY, NEITHER = "applied", "to apply", "neither"
GENERALITY_KEYS = ("pack", "dev", "first_sight", "class_recall", "registry_changes", "gate17_hits", "case_file_changes")
BEFORE_GENERALITY = ("RP1", "RP2", "ST1", "ST2", "ST3", "ST4", "ST5", "ST5B", "U1", "U2")

def _no_comment(line: str) -> str:
  for m in re.finditer(r"#", line):
    before = line[:m.start()]
    if before.strip() and before[-1:].isspace() and before.count('"') % 2 == 0 and before.count("'") % 2 == 0:
      return before
  return line

def norm(text: str) -> str:
  lines = [_no_comment(ln).rstrip() for ln in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
  while lines and not lines[0]:
    lines.pop(0)
  while lines and not lines[-1]:
    lines.pop()
  return "\n".join(lines)

def sha256_of(path: pathlib.Path) -> str:
  return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()

def parse_md(text: str) -> dict:
  edits = []
  
  parts = re.split(r"(?m)^### `([^`]+)`[ \t]*$", text)
  for i in range(1, len(parts), 2):
    path, body = parts[i], parts[i + 1]
    for chunk in re.split(r"(?m)^#### Edit ", body)[1:]:
      m = re.match(r"(\d+)", chunk)
      blocks = re.findall(r"```[A-Za-z]*\n(.*?)\n```", chunk, re.S)
      if m and len(blocks) >= 2:
        edits.append({"n": int(m.group(1)), "file": path, "find": blocks[0], "replace": blocks[1]})
        
  manifest = None
  for block in re.findall(r"```yaml\n(.*?)\n```", text, re.S):
    if re.search(r"(?m)^pack:", block):
      import yaml
      manifest = yaml.safe_load(block)
      break
  new_files = []
  if manifest is None:
    m = re.search(r"\*\*New files\*\*[^\n]*\n(.*?)(?:\n\n[^-\n]|\n#|\Z)", text, re.S)
    if m:
      new_files = re.findall(r"^- `([^`]+)`", m.group(1), re.M)
  return {"edits": edits, "manifest": manifest, "new_files": new_files}

def _pack_id(name: str) -> str:
  return re.sub(r"[^A-Z0-9]", "", str(name).upper())

def generality_problems(text: str, manifest: dict | None) -> list:
  pack = _pack_id((manifest or {}).get("pack") or "")
  if not pack or pack.isdigit() or pack in BEFORE_GENERALITY:
    return []
  
  head = re.search(r"(?m)^##\s*(?:\d+\.\s*)?Generality\b.*$", text)
  if not head:
    return ["the pack md has no Generality section"]
  rest = text[head.end():]
  nxt = re.search(r"(?m)^##\s", rest)
  body = rest[:nxt.start()] if nxt else rest
  import yaml
  for block in re.findall(r"```yaml\n(.*?)\n```", body, re.S):
    try:
      doc = yaml.safe_load(block)
    except yaml.YAMLError:
      continue
    if isinstance(doc, dict) and isinstance(doc.get("generality"), dict):
      rec = doc["generality"]
      missing = [k for k in GENERALITY_KEYS if k not in rec]
      if missing:
        return [f"the generality record lacks {', '.join(missing)}"]
      if _pack_id(rec["pack"]) != pack:
        return [f"the generality record names pack {rec['pack']}, the manifest names {(manifest or {}).get('pack')}"]
      return []
    
  return ["the Generality section has no `generality:` record in a yaml block"]

def block_state(tree_text: str, find: str, replace: str) -> tuple:
  f, r, t = norm(find), norm(replace), norm(tree_text)
  in_replace = r.count(f) if f else 0
  n_rep, n_find = t.count(r) if r else 0, t.count(f) if f else 0
  left = n_find - n_rep * in_replace
  
  if n_rep and left <= 0:
    return APPLIED, ""
  if left > 0:
    return TO_APPLY, ("the REPLACE text is also present" if n_rep else "" if n_find == 1 else f"the FIND text occurs {n_find} times in the file now")
  return NEITHER, ""

def resolve(root: pathlib.Path, rel: str) -> pathlib.Path:
  p = pathlib.PurePosixPath(rel)
  if root.name == "backend" and p.parts and p.parts[0] == "backend":
    return root.joinpath(*p.parts[1:])
  return root.joinpath(*p.parts)

def default_root() -> pathlib.Path:
  here = pathlib.Path(__file__).resolve()
  for parent in here.parents:
    if parent.name == "backend":
      return parent.parent
  return pathlib.Path.cwd()

def placement_problems(root: pathlib.Path) -> list:
  top = root.parent if root.name == "backend" else root
  app = top / "backend" / "app"
  out = []
  if app.is_dir():
    for folder, dirs, names in os.walk(app):
      dirs[:] = [d for d in dirs if d != "__pycache__"]
      here = pathlib.Path(folder)
      if here.name != "prompts":
        continue
      for name in sorted(names):
        if name.endswith(".py") and name != "__init__.py":
          home = here.parent.relative_to(top).as_posix()
          out.append(f"{(here / name).relative_to(top).as_posix()} is a module inside a prompts folder, which holds __init__.py and .yaml files only; it belongs at {home}/{name}")

  if app.is_dir():
    for folder, dirs, names in os.walk(app):
      dirs[:] = [d for d in dirs if d not in ("__pycache__", "proof")]
      for name in sorted(names):
        if name.endswith(".py"):
          p = pathlib.Path(folder) / name
          if "standards_draft" in p.read_text(encoding="utf8", errors="replace"):
            out.append(f"{p.relative_to(top).as_posix()} names standards_draft; the web drafts are read inside proof/ only, never by a run")

  if (top / ".git").exists():
    try:
      got = subprocess.run(["git", "--no-optional-locks", "-C", str(top), "ls-files", "-ci", "--exclude-standard"], capture_output=True, text=True, timeout=60).stdout.splitlines()
    except (OSError, subprocess.SubprocessError):
      got = []
    out += [f"{p.strip()} is tracked but .gitignore ignores it; run: git rm --cached {p.strip()}" for p in got if p.strip()]
  else:
    skip = {"__pycache__", "node_modules", "venv", ".venv"}
    for folder, dirs, names in os.walk(top / "backend"):
      dirs[:] = [d for d in dirs if d not in skip]
      out += [f"{(pathlib.Path(folder) / n).relative_to(top).as_posix()} is a backup file; delete it" for n in sorted(names) if ".bak" in n]
  return out

def check(md_path: pathlib.Path, root: pathlib.Path, before: bool = False) -> tuple:
  doc = parse_md(md_path.read_text(encoding="utf8"))
  out, misses = [], 0
  counts = {APPLIED: 0, TO_APPLY: 0, NEITHER: 0}
  
  for e in doc["edits"]:
    path = resolve(root, e["file"])
    if not path.is_file():
      out.append(f"Edit {e['n']:>3}  FILE MISSING   {e['file']}")
      misses += 1
      continue
    state, note = block_state(path.read_text(encoding="utf8", errors="replace"), e["find"], e["replace"])
    counts[state] += 1
    bad = state in (APPLIED, NEITHER) if before else state != APPLIED
    misses += 1 if bad else 0
    out.append(f"Edit {e['n']:>3}  {state.upper():9}" + ("  <-- " + ("not applied" if state == TO_APPLY else "cannot be applied here" if state == NEITHER else "already applied") if bad else "") + f"   {e['file']}" + (f"   ({note})" if note else ""))
    
  mf = doc["manifest"] or {}
  for nf in mf.get("new_files") or []:
    p = resolve(root, nf["path"])
    if not p.is_file():
      out.append(f"New file   MISSING   {nf['path']}")
      misses += 0 if before else 1
    elif sha256_of(p) != nf.get("sha256"):
      out.append(f"New file   DIFFERS   {nf['path']}  (sha256 {sha256_of(p)[:12]}, the manifest lists {str(nf.get('sha256'))[:12]})")
      misses += 0 if before else 1
    else:
      out.append(f"New file   ok         {nf['path']}")
      
  for nf in doc["new_files"]:
    ok = resolve(root, nf).is_file()
    out.append(f"New file   {'ok' if ok else 'MISSING':9}  {nf}  (no manifest: existence only)")
    misses += 0 if before else (0 if ok else 1)
    
  for gone in mf.get("deleted_files") or []:
    still = resolve(root, gone).exists()
    out.append(f"Deleted    {'STILL THERE' if still else 'ok':11}{gone}")
    misses += 0 if before else (1 if still else 0)
  for problem in generality_problems(md_path.read_text(encoding="utf8"), doc["manifest"]):
    out.append(f"Generality {problem}")
    misses += 1
  listed = {n for ed in (mf.get("edits") or []) for n in ed.get("blocks") or []}
  have = {e["n"] for e in doc["edits"]}
  if mf and listed != have:
    out.append(f"Manifest   lists blocks {sorted(listed - have)} that have no text and misses blocks {sorted(have - listed)}")
    
    misses += 1
  if not before:
    for problem in placement_problems(root):
      out.append(f"Placement  {problem}")
      misses += 1
  out.append(f"{len(doc['edits'])} edit block(s): {counts[APPLIED]} applied, {counts[TO_APPLY]} to apply, {counts[NEITHER]} neither; {misses} miss(es)" + (" (checking before applying)" if before else ""))
  return out, misses

def main(argv: list | None = None) -> int:
  ap = argparse.ArgumentParser(description="Check that a pack's FIND / REPLACE blocks and new files are in the tree.")
  ap.add_argument("md", help="the PACKnnn_find_replace.md file")
  
  ap.add_argument("--root", help="the project folder (the one with backend/ and frontend/), or its backend folder; default: found from this file")
  ap.add_argument("--before", action="store_true", help="the check before applying: every block should be 'to apply'")
  args = ap.parse_args(argv)
  root = pathlib.Path(args.root).resolve() if args.root else default_root()
  md = pathlib.Path(args.md)
  
  if not md.is_file():
    print(f"{md} is not a file.")
    return 2
  lines, misses = check(md, root, args.before)
  print("\n".join(lines))
  return 1 if misses else 0

if __name__ == "__main__":
  sys.exit(main())
