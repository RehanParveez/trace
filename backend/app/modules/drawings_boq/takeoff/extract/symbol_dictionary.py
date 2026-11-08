from __future__ import annotations

RULE, AI_READ, VOCABULARY, UNREAD = "RULE", "AI_READ", "VOCABULARY", "UNREAD"

def found(lists: list) -> dict:
  out: dict = {}
  for entries in lists:
    for e in entries or []:
      out.setdefault(e["name"], e)
  return out

def apply(rows: list, entries: dict, placed) -> list:
  if not entries:
    return rows
  out = []
  for r in rows:
    e = entries.get(r.get("name"))
    out.append({**r, "kind": e["kind"], "kind_source": AI_READ, "kind_quote": e.get("quote")} if e and not placed(r.get("name")) else r)
  return out

def kinds_of(rows: list) -> dict:
  return {r["name"]: r["kind"] for r in rows if r.get("kind")}

def dictionary(rows: list, kind_of, other: str, item_of, from_vocabulary=lambda name: False) -> list:
  out = []
  for r in rows:
    rule = kind_of(r.get("name"))
    kind = r.get("kind") or (rule if rule != other else None)
    source = AI_READ if r.get("kind") else VOCABULARY if from_vocabulary(r.get("name")) else RULE if rule != other else UNREAD
    objects = len(r.get("objects") or [])
    out.append({"name": r.get("name"), "description": r.get("description"), "kind": kind, "item": item_of(kind) if kind else None, "source": source,
      "counted_by": "TEXT" if r.get("token") and objects < 3 else "SHAPE" if objects else "NONE", "objects": objects, "page_no": r.get("page_no"), "quote": r.get("kind_quote")})
  return out
