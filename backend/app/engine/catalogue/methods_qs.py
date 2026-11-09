from __future__ import annotations
import functools
import os
import re
import yaml
from app.engine.catalogue import loader as CAT

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "methods_qs.yaml")
ASPECTS = ("deductions", "faces", "heights", "laps", "wastage", "working_space", "projections")
QS, WORKBOOK, STANDARD = "QS", "WORKBOOK", "STANDARD"
METHOD, FACT, CHOICE = "METHOD", "FACT", "CHOICE"
MARKER_KEY = "qs_method.profile"
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

class MethodError(Exception):
  pass

def _raw(path: str = PATH) -> dict:
  with open(path, encoding="utf-8") as fh:
    data = yaml.safe_load(fh)
  if not isinstance(data, dict) or not isinstance(data.get("profiles"), list):
    raise MethodError("methods_qs.yaml must hold a profiles list")
  return data

def _text(x) -> bool:
  return isinstance(x, str) and bool(x.strip())

def source_problems(mid: str, src) -> list:
  out: list = []
  
  if not isinstance(src, dict):
    return [f"{mid}: a method has no source"]
  kind = src.get("kind")
  if kind == QS:
    if not _text(src.get("name")):
      out.append(f"{mid}: a QS source names the QS")
    if not (isinstance(src.get("date"), str) and DATE.match(src["date"])):
      out.append(f"{mid}: a QS source has the date of the answer, as YYYY-MM-DD")
    if not _text(src.get("reading")):
      out.append(f"{mid}: a QS source names the reading that holds his words")
  elif kind == WORKBOOK:
    for f in ("qs", "workbook", "sheet", "cell"):
      if not _text(src.get(f)):
        out.append(f"{mid}: a WORKBOOK source has {f}")
    if src.get("confirmed") is not False and src.get("confirmed") is not True:
      out.append(f"{mid}: a WORKBOOK source says whether the QS has confirmed it (confirmed: true or false)")
  elif kind == STANDARD:
    out.append(f"{mid}: a standard is not a QS method; put it under `open`")
  else:
    out.append(f"{mid}: the source kind must be {QS} or {WORKBOOK}")
  return out

def problems(path: str = PATH) -> list:
  out: list = []
  data = _raw(path)
  items = {i.id for i in CAT.items()}
  seen: set = set()
  seen_rule: dict = {}
  pids: set = set()
  
  for p in data["profiles"]:
    pid = str(p.get("id") or "?")
    if pid in pids:
      out.append(f"profile {pid}: id used twice")
    pids.add(pid)
    for f in ("label", "qs", "methods"):
      if not p.get(f):
        out.append(f"profile {pid}: missing {f}")
        
    for m in p.get("methods") or []:
      mid = str(m.get("id") or "?")
      if mid in seen:
        out.append(f"method {mid}: id used twice")
      seen.add(mid)
      if m.get("aspect") not in ASPECTS:
        out.append(f"{mid}: aspect must be one of {', '.join(ASPECTS)}")
      if m.get("item") != "ALL" and m.get("item") not in items:
        out.append(f"{mid}: item {m.get('item')} is not in the catalogue")
      if not _text(m.get("says")):
        out.append(f"{mid}: says what the QS does, in a sentence")
      rule = m.get("rule")
      
      if not (isinstance(rule, dict) and _text(rule.get("key")) and "value" in rule and isinstance(rule.get("scope", {}), dict) and rule.get("value") is not None):
        out.append(f"{mid}: a rule has a key, a scope and a value")
      else:
        k = (pid, rule["key"], repr(sorted((rule.get("scope") or {}).items())))
        if k in seen_rule:
          out.append(f"{mid}: sets the same rule as {seen_rule[k]}")
        seen_rule[k] = mid
        if rule["key"] in set(data.get("building_facts") or []):
          out.append(f"{mid}: {rule['key']} is a fact of one building, not a method")
      out += source_problems(mid, m.get("source"))
      src = m.get("source") or {}
      if src.get("kind") == QS and _text(src.get("name")) and p.get("qs") and src["name"] != p["qs"]:
        out.append(f"{mid}: the source is {src['name']} and the profile is {p['qs']}")
      for a in m.get("also_seen") or []:
        if not (isinstance(a, dict) and "value" in a and _text(a.get("workbook")) and _text(a.get("sheet")) and _text(a.get("cell"))):
          out.append(f"{mid}: also_seen needs a value, a workbook, a sheet and a cell")
          
  oseen: set = set()
  for o in data.get("open") or []:
    oid = str(o.get("id") or "?")
    if oid in oseen:
      out.append(f"open {oid}: id used twice")
    oseen.add(oid)
    
    if o.get("aspect") not in ASPECTS or not _text(o.get("question")) or not _text(o.get("trace")):
      out.append(f"open {oid}: needs an aspect, a question and what Trace holds")
    if o.get("standard") is not None and not str(o["standard"]).startswith("Standard: "):
      out.append(f"open {oid}: a standard is written 'Standard: ' and the standard")
    if o.get("item") != "ALL" and o.get("item") not in items:
      out.append(f"open {oid}: item {o.get('item')} is not in the catalogue")
      
  both = set(data.get("building_facts") or []) & set(data.get("choices") or [])
  if both:
    out.append(f"{', '.join(sorted(both))} is listed as a fact and as a choice")
  return out

@functools.lru_cache(maxsize=1)
def _load() -> dict:
  bad = problems()
  if bad:
    raise MethodError("; ".join(bad[:5]) + (f"; and {len(bad) - 5} more" if len(bad) > 5 else ""))
  return _raw()

def reload() -> None:
  _load.cache_clear()

def profiles() -> list:
  return list(_load()["profiles"])

def profile(pid: str) -> dict | None:
  return next((p for p in profiles() if p["id"] == pid), None)

def open_questions() -> list:
  return list(_load().get("open") or [])

def entries(pid: str) -> list:
  p = profile(pid)
  if p is None:
    raise MethodError(f"no QS method profile {pid}")
  return list(p["methods"])

def rule_id(method: dict) -> tuple:
  r = method["rule"]
  return r["key"], tuple(sorted((r.get("scope") or {}).items()))

def source_text(src: dict) -> str:
  if src["kind"] == QS:
    return f"{src['name']}, {src['date']} (reading {src['reading']})"
  return f"{src['qs']}'s workbook {src['workbook']}, sheet {src['sheet']}, cell {src['cell']}" + ("" if src.get("confirmed") else "; read from his totals, not confirmed by him")

def rules(pid: str) -> list:
  out = []
  for m in entries(pid):
    r = m["rule"]
    out.append({"id": m["id"], "key": r["key"], "scope": dict(r.get("scope") or {}), "value": r["value"], "aspect": m["aspect"], "item": m["item"], "says": m["says"],
      "note": f"QS method {pid}: {m['says']} Source: {source_text(m['source'])}.", "source": source_text(m["source"]), "confirmed": m["source"]["kind"] == QS or bool(m["source"].get("confirmed"))})
  return out

def method_keys() -> frozenset:
  return frozenset(m["rule"]["key"] for p in profiles() for m in p["methods"])

def building_fact_keys() -> frozenset:
  return frozenset(_load().get("building_facts") or [])

def choice_keys() -> frozenset:
  return frozenset(_load().get("choices") or [])

def kind_of(key: str) -> str | None:
  if key in method_keys():
    return METHOD
  if key in building_fact_keys():
    return FACT
  if key in choice_keys():
    return CHOICE
  return None

def method_for(key: str, scope: dict | None = None, pid: str | None = None) -> dict | None:
  want = tuple(sorted((scope or {}).items()))
  for p in profiles():
    if pid and p["id"] != pid:
      continue
    for m in p["methods"]:
      if m["rule"]["key"] == key and tuple(sorted((m["rule"].get("scope") or {}).items())) == want:
        return m
  return None
