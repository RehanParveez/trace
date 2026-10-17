from __future__ import annotations
import hashlib
import os
import json
from app.modules.drawings_boq.takeoff.proof import known_facts as KF

def sha256_of(path: str) -> str:
  h = hashlib.sha256()
  with open(path, "rb") as fh:
    for block in iter(lambda: fh.read(1 << 20), b""):
      h.update(block)
  return h.hexdigest()

def load(folder: str) -> dict:
  """The case of a folder, with its facts normalised. Raises ValueError with a plain sentence when the file is not usable."""
  path = os.path.join(folder, "case.json")
  if not os.path.isfile(path):
    raise ValueError(f"{folder} has no case.json.")
  with open(path, encoding="utf-8") as fh:
    try:
      raw = json.load(fh)
      
    except json.JSONDecodeError as e:
      raise ValueError(f"{path} is not valid JSON: {e}.")
  if not raw.get("case"):
    raise ValueError(f"{path} has no case id.")
  drawings = raw.get("drawings") or []
  
  if not drawings or not all(d.get("file") for d in drawings):
    raise ValueError(f"{path} lists no drawing file.")
  facts = []
  for i, f in enumerate(raw.get("facts") or []):
    try:
      one = KF.normalise(f)
    except ValueError as e:
      raise ValueError(f"{path}, fact {i + 1}: {e}")
    if f.get("known"):
      one["known"] = str(f["known"])
    if f.get("note"):
      one["note"] = str(f["note"])
    facts.append(one)
    
  if not facts:
    raise ValueError(f"{path} has no facts.")
  return {"case": str(raw["case"]), "name": raw.get("name") or str(raw["case"]), "notes": raw.get("notes"), "drawings": drawings, "facts": facts, "folder": folder}

def verify_files(case: dict) -> list:
  """Problems with the drawing files of a case: [] when every file is there and is the file the case was made for."""
  out = []
  
  for d in case["drawings"]:
    p = os.path.join(case["folder"], d["file"])
    if not os.path.isfile(p):
      out.append(f"{d['file']} is not in {case['folder']}.")
    elif d.get("sha256") and sha256_of(p) != d["sha256"]:
      out.append(f"{d['file']} is not the file this case was made for (its hash differs).")
  return out

def judge(case: dict, results: list) -> dict:
  """{"ok", "regressions": [...], "news": [...], "tally"}: the results of KF.check for the facts of the case, held against the case file."""
  regressions, news = [], []
  
  for fact, r in zip(case["facts"], results):
    if fact.get("known"):
      if r["status"] == KF.PASS:
        news.append(f"{r['text']}: now as the drawing prints it (it was accepted as different because: {fact['known']}). Take 'known' off this fact.")
    elif r["status"] != KF.PASS:
      regressions.append(f"{r['text']}: {r['message']}")
  return {"ok": not regressions and not news, "regressions": regressions, "news": news, "tally": KF.tally(results)}
