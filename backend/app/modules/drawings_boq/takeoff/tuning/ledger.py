from __future__ import annotations
import json
import pathlib
from app.modules.drawings_boq.takeoff.extract import config as C
from app.modules.drawings_boq.takeoff.tuning import registry as R

BASE_EXTRACT_VERSION = 30       
PATH = pathlib.Path(__file__).with_name("ledger.json")
ENTRY_FIELDS = ("key", "from", "to", "extract_version", "evidence")

def load(path: pathlib.Path = PATH) -> list:
  data = json.loads(path.read_text(encoding="utf-8"))
  return list(data.get("entries", []))

def dumps(entries: list) -> str:
  return json.dumps({"ledger_version": 1, "base_extract_version": BASE_EXTRACT_VERSION, "entries": entries}, indent=2, sort_keys=True) + "\n"

def same(a, b) -> bool:
  return abs(float(a) - float(b)) <= 1e-9 * max(1.0, abs(float(a)), abs(float(b)))

def drift(entries: list | None = None, extract_version: int | None = None) -> list:
  entries = load() if entries is None else entries
  ev = C.EXTRACT_VERSION if extract_version is None else extract_version
  by = R.by_key()
  out = []
  latest: dict = {}
  for e in entries:
    miss = [f for f in ENTRY_FIELDS if f not in e]
    if miss:
      out.append(f"A ledger entry lacks {', '.join(miss)}.")
      continue
  
    if e["key"] not in by:
      out.append(f"The ledger names {e['key']}, which is not in the register.")
      continue
    if not isinstance(e["evidence"], dict) or not e["evidence"]:
      out.append(f"The ledger entry for {e['key']} carries no evidence.")
    if e["extract_version"] > ev:
      out.append(f"The ledger entry for {e['key']} is for EXTRACT_VERSION {e['extract_version']}, which is ahead of the code ({ev}).")
    if e["extract_version"] <= BASE_EXTRACT_VERSION:
      out.append(f"The ledger entry for {e['key']} is for EXTRACT_VERSION {e['extract_version']}; a calibration needs a version above {BASE_EXTRACT_VERSION}.")
    prev = latest.get(e["key"])
    
    if prev is None:
      if not same(e["from"], by[e["key"]].hand):
        out.append(f"The first ledger entry for {e['key']} starts from {e['from']}, not from its hand value {by[e['key']].hand}.")
    elif not same(e["from"], prev["to"]):
      out.append(f"The ledger entries for {e['key']} do not follow each other ({prev['to']} then from {e['from']}).")
    latest[e["key"]] = e
    
  for p in by.values():
    e = latest.get(p.key)
    live = p.live
    if e is None:
      if not same(live, p.hand):
        out.append(f"{p.key} is {live}, not its hand value {p.hand}, and the ledger has no entry for it.")
    elif not same(live, e["to"]):
      out.append(f"{p.key} is {live}, but the ledger says it was set to {e['to']}.")
  if any(not same(p.live, p.hand) for p in by.values()) and ev <= BASE_EXTRACT_VERSION:
    out.append(f"A constant differs from its hand value but EXTRACT_VERSION is still {ev}: raise it above {BASE_EXTRACT_VERSION} so the stored reads become stale.")
  return out
