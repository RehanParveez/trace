from __future__ import annotations
import os
from typing import NamedTuple
import yaml
from app.modules.drawings_boq.takeoff.proof import case_io as CIO
from app.modules.drawings_boq.takeoff.proof import case as CASE
from app.modules.drawings_boq.takeoff.proof.reading.formats import KEY_LEN

READING = "reading"
OFFICES = {"IsbP": "A", "bbs_156": "A", "2053c": "B", "350c": "B", "925b": "B", "959n": "B", "201cd": "B", "909a": "B", "191c": "C", "plot1": "D", "652d": "E"}
UNKNOWN_OFFICE = "?"

class SetRef(NamedTuple):
  case: str
  pdf: str
  pdf_path: str | None
  pdf_key: str
  truth_folder: str
  owner: str
  link: bool
  office: str = UNKNOWN_OFFICE

def office_of(case: str) -> str:
  return OFFICES.get(case, UNKNOWN_OFFICE)

def _raw_case(folder: str) -> dict:
  with open(os.path.join(folder, "case.yaml"), encoding="utf-8") as fh:
    return yaml.safe_load(fh) or {}

def find_sets(cases_dir: str | None = None, root: str = CIO.HERE) -> list:
  files_dir = CIO.cases_dir(cases_dir)
  refs, owners, problems = [], {}, []
  for name in CIO.list_cases(root, audit=True):
    folder = os.path.join(root, name)
    raw = _raw_case(folder)
    shas = raw.get("sha256") or {}
    for pdf in raw.get("pdfs") or []:
      path = os.path.join(files_dir, pdf) if files_dir and os.path.isfile(os.path.join(files_dir, pdf)) else None
      sha = shas.get(pdf) or (CASE.sha256_of(path) if path else None)
      if not sha:
        problems.append(f"{name}: {pdf} has no sha256 in case.yaml and is not in the PDF folder, so its key cannot be made.")
        continue
      key = str(sha)[:KEY_LEN]
      owner = owners.setdefault(key, name)
      refs.append(SetRef(case=name, pdf=pdf, pdf_path=path, pdf_key=key, truth_folder=os.path.join(root, owner, READING, key), owner=owner, link=owner != name, office=office_of(owner)))
      
  if problems:
    raise ValueError("\n".join(problems))
  return refs

def link_path(ref: SetRef, root: str = CIO.HERE) -> str:
  return os.path.join(root, ref.case, READING, ref.pdf_key + ".link")
