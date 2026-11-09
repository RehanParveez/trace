from __future__ import annotations
import functools
import os
import re
import yaml

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bar_grammar.yaml")
OFFICES = ("A", "B", "C", "D", "E")
ON, SEEN_ONCE = "active", "seen_once"
KINDS = ("rewrite", "count", "spacing")
MIN_OFFICES = 2

@functools.lru_cache(maxsize=1)
def doc() -> dict:
  with open(PATH, encoding="utf-8") as fh:
    return yaml.safe_load(fh) or {}

def forms(kind: str | None = None, status: str | None = ON) -> list:
  return [f for f in doc().get("forms") or [] if (kind is None or f.get("kind") == kind) and (status is None or f.get("status") == status)]

@functools.lru_cache(maxsize=1)
def rewrites() -> tuple:
  return tuple((re.compile(f["find"], re.I if "I" in str(f.get("flags") or "") else 0), f["replace"]) for f in forms("rewrite"))

@functools.lru_cache(maxsize=1)
def count_pattern() -> str:
  return "|".join(f["pattern"] for f in sorted(forms("count"), key=lambda f: -len(f["pattern"])))

def count_value(text: str) -> int:
  return sum(int(x) for x in re.findall(r"\d+", text or ""))

def offices_of(form: dict) -> set:
  return {e.get("office") for e in form.get("examples") or []}

def problems(d: dict | None = None) -> list:
  d = doc() if d is None else d
  out: list = []
  seen: set = set()
  for f in d.get("forms") or []:
    fid = f.get("id")
    if not fid or fid in seen:
      out.append(f"bar_grammar.yaml: form {fid!r} has no id or repeats one")
    seen.add(fid)
    
    if f.get("kind") not in KINDS:
      out.append(f"bar_grammar.yaml: {fid} kind must be one of {', '.join(KINDS)}")
    if f.get("status") not in (ON, SEEN_ONCE):
      out.append(f"bar_grammar.yaml: {fid} status must be active or seen_once")
    for key in ("find", "replace") if f.get("kind") == "rewrite" else ("pattern",):
      if key not in f:
        out.append(f"bar_grammar.yaml: {fid} needs {key}")
    for key in ("find", "pattern"):
      if key in f:
        try:
          re.compile(f[key])
        except re.error as e:
          out.append(f"bar_grammar.yaml: {fid} {key} does not compile: {e}")
          
    bad = sorted(o for o in offices_of(f) if o not in OFFICES)
    if bad:
      out.append(f"bar_grammar.yaml: {fid} has examples from unknown offices {bad}")
    n = len({o for o in offices_of(f) if o in OFFICES})
    if f.get("status") == ON and n < MIN_OFFICES:
      out.append(f"bar_grammar.yaml: {fid} is active with examples from {n} office(s); it needs {MIN_OFFICES}")
    if f.get("status") == SEEN_ONCE and n >= MIN_OFFICES:
      out.append(f"bar_grammar.yaml: {fid} has examples from {n} offices; it can be made active")
    if not f.get("examples"):
      out.append(f"bar_grammar.yaml: {fid} has no examples")
  return out

def example_problems() -> list:
  from app.engine.measure import steel_grammar as SG
  out: list = []
  for f in forms(None, ON):
    for e in f.get("examples") or []:
      if f["kind"] == "rewrite":
        got = SG.normalise(e["text"])
        if got != e["expect"]:
          out.append(f"{f['id']}: {e['text']!r} reads as {got!r}, expected {e['expect']!r}")
      elif f["kind"] == "count":
        bars = SG.parse_callout(e["text"])["bars"]
        first = bars[0] if bars else {}
        if any(first.get(k) != v for k, v in e["expect"].items()):
          out.append(f"{f['id']}: {e['text']!r} reads as {first or 'nothing'}, expected {e['expect']}")
  return out
