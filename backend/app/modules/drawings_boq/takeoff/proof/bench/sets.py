from __future__ import annotations
import os
import yaml
from app.modules.drawings_boq.takeoff.proof import census as CEN
from app.modules.drawings_boq.takeoff.proof import case_io as CIO
from app.engine.catalogue import loader as CL
from app.modules.drawings_boq.takeoff.proof.reading import sets as RS

HERE = os.path.dirname(os.path.abspath(__file__))
DEV, TEST, FIRST_SIGHT, UNSPLIT = "DEV", "TEST", "FIRST_SIGHT", "UNSPLIT"
SPLIT_KEYS = (("dev", DEV), ("test", TEST), ("first_sight", FIRST_SIGHT))

def load(path: str | None = None) -> dict:
  with open(path or os.path.join(HERE, "sets.yaml"), encoding="utf-8") as fh:
    return yaml.safe_load(fh) or {}

def group_of(section: str, doc: dict) -> str | None:
  return next((g for g, names in (doc.get("section_groups") or {}).items() if section in names), None)

def split_of(office: str, group: str, splits: dict | None = None) -> str:
  groups = (splits if splits is not None else CEN.splits()).get("groups") or {}
  row = groups.get(group) or {}
  return next((label for key, label in SPLIT_KEYS if office in (row.get(key) or [])), UNSPLIT)

def problems(doc: dict | None = None, root: str = CIO.HERE) -> list:
  doc = doc or load()
  bad = []
  sets = doc.get("sets") or {}
  on_disk = set(CIO.list_cases(root, audit=True))
  for name in sorted(on_disk - set(sets)):
    bad.append(f"case {name} is not in sets.yaml")
  for name in sorted(set(sets) - on_disk):
    bad.append(f"sets.yaml names {name}, which is not a case folder")
  for name, row in sorted(sets.items()):
    if not row.get("office"):
      bad.append(f"{name} has no office letter")
    elif RS.office_of(name) != row["office"]:
      bad.append(f"{name}: sets.yaml says office {row['office']}, the reading sets say {RS.office_of(name)}")
      
  splits = CEN.splits().get("groups") or {}
  for group in doc.get("section_groups") or {}:
    if group not in splits:
      bad.append(f"section group {group} has no split in reading/splits.yaml")
  seen: dict = {}
  for group, names in (doc.get("section_groups") or {}).items():
    for n in names:
      if n in seen:
        bad.append(f"section {n} is in {seen[n]} and {group}")
      seen[n] = group
  for section in sorted({it.section for it in CL.items()}):
    if section not in seen:
      bad.append(f"catalogue section {section} is in no section group")
  return bad
