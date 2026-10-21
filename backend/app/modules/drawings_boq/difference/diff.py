from __future__ import annotations

SAME_PCT = 0.01
MIN_CHANGE_PCT = 0.5
MEMBER_CAP = 15
STOREY_CAP = 12
TINY = 1e-9
VOLATILE_SETTINGS = ("level_names", "project_id", "scope_drawings", "scope_overlaps")
SETTINGS_CAP = 30

def row_from(code: str, unit: str, source: str | None, quantity, level: str | None, trace: dict | None, global_id: str | None = None, element_name: str | None = None) -> dict:
  inputs = (trace or {}).get("inputs") or {}
  src = inputs.get("formwork_source") or inputs.get("steel_source") or {}
  tag = inputs.get("tag") or src.get("tag")
  tag = str(tag).strip() if tag not in (None, "") else None
  lvl = (level or "").strip() or None
  key = f"g:{global_id}" if global_id else (f"t:{lvl or ''}|{tag.upper()}" if tag else None)
  return {"code": code, "unit": unit, "source": source or "MODEL", "quantity": float(quantity or 0), "level": lvl, "key": key, "label": tag or (element_name or None)}

def aggregate(rows) -> dict:
  out: dict = {}
  
  for r in rows:
    slot = out.setdefault((r["code"], r["unit"]), {"total": 0.0, "rows": 0, "levels": {}, "members": {}, "sources": {}})
    q = float(r["quantity"])
    slot["total"] += q
    slot["rows"] += 1
    lv = r.get("level") or "(no storey)"
    slot["levels"][lv] = slot["levels"].get(lv, 0.0) + q
    slot["sources"][r.get("source") or "MODEL"] = slot["sources"].get(r.get("source") or "MODEL", 0.0) + q
    
    if r.get("key"):
      m = slot["members"].setdefault(r["key"], {"label": r.get("label") or r["key"], "level": r.get("level"), "qty": 0.0})
      m["qty"] += q
  return out

def _pct(delta: float, before: float):
  return None if abs(before) <= TINY else delta / before * 100.0

def _same(a: float, b: float, same_pct: float) -> bool:
  return abs(b - a) <= max(abs(a), abs(b)) * same_pct / 100.0 + TINY

def _split(a: dict, b: dict, same_pct: float, cap: int) -> list:
  out = []
  for k in set(a) | set(b):
    x, y = a.get(k, 0.0), b.get(k, 0.0)
    if not _same(x, y, same_pct):
      out.append({"name": k, "a": round(x, 6), "b": round(y, 6), "delta": round(y - x, 6)})
  out.sort(key=lambda d: (-abs(d["delta"]), d["name"]))
  return out[:cap] if cap else out

def _members(a: dict, b: dict, same_pct: float) -> tuple:
  out = []
  for k in set(a) | set(b):
    ma, mb = a.get(k), b.get(k)
    qa, qb = (ma or {}).get("qty", 0.0), (mb or {}).get("qty", 0.0)
    
    if ma is None:
      status = "ADDED"
    elif mb is None:
      status = "REMOVED"
    elif _same(qa, qb, same_pct):
      continue
    else:
      status = "CHANGED"
    ref = mb or ma
    out.append({"label": ref["label"], "level": ref.get("level"), "status": status, "a": round(qa, 6), "b": round(qb, 6), "delta": round(qb - qa, 6)})
  out.sort(key=lambda d: (-abs(d["delta"]), str(d["label"])))
  return out[:MEMBER_CAP], len(out)

def diff_runs(a_rows, b_rows, same_pct: float = SAME_PCT, names: dict | None = None) -> dict:
  A, B = aggregate(a_rows), aggregate(b_rows)
  items = []
  for (code, unit) in set(A) | set(B):
    x, y = A.get((code, unit)), B.get((code, unit))
    ta, tb = (x or {}).get("total", 0.0), (y or {}).get("total", 0.0)
    
    if x is None:
      status = "ADDED"
    elif y is None:
      status = "REMOVED"
    elif _same(ta, tb, same_pct):
      status = "SAME"
    else:
      status = "CHANGED"
    srcs = [{"source": d["name"], "a": d["a"], "b": d["b"], "delta": d["delta"]}
      for d in _split((x or {}).get("sources", {}), (y or {}).get("sources", {}), 1.0 if status == "SAME" else same_pct, 0)] if (x and y) else []
    moved = bool(srcs) and status == "SAME" and any(abs(s["delta"]) > max(abs(ta), 1.0) * 0.01 for s in srcs)
    item = {"code": code, "name": (names or {}).get(code), "unit": unit, "status": status, "a": round(ta, 6), "b": round(tb, 6), "delta": round(tb - ta, 6),
      "pct": None if x is None else (None if _pct(tb - ta, ta) is None else round(_pct(tb - ta, ta), 3)), "rows_a": (x or {}).get("rows", 0), "rows_b": (y or {}).get("rows", 0),
      "storeys": [], "members": [], "members_changed": 0, "sources": srcs, "source_moved": moved}
    
    if status != "SAME":
      item["storeys"] = [{"level": d["name"], "a": d["a"], "b": d["b"], "delta": d["delta"]} for d in _split((x or {}).get("levels", {}), (y or {}).get("levels", {}), same_pct, STOREY_CAP)]
      item["members"], item["members_changed"] = _members((x or {}).get("members", {}), (y or {}).get("members", {}), same_pct)
    items.append(item)
  order = {"CHANGED": 0, "ADDED": 1, "REMOVED": 2, "SAME": 3}
  items.sort(key=lambda i: (order[i["status"]], -(abs(i["pct"]) if i["pct"] is not None else 1e12), i["code"], i["unit"]))
  count = lambda s: sum(1 for i in items if i["status"] == s)
  return {"same_pct": same_pct, "items": items,
    "measures": {"items": len(items), "same": count("SAME"), "changed": count("CHANGED"), "added": count("ADDED"), "removed": count("REMOVED"),
      "source_moved": sum(1 for i in items if i["source_moved"]), "rows_a": sum(s["rows"] for s in A.values()), "rows_b": sum(s["rows"] for s in B.values())}}

def _flatten(value, prefix: str = "") -> dict:
  if isinstance(value, dict):
    out: dict = {}
    
    for k, v in value.items():
      if not prefix and k in VOLATILE_SETTINGS:
        continue
      out.update(_flatten(v, f"{prefix}.{k}" if prefix else str(k)))
    return out
  if isinstance(value, (list, tuple)):
    return {prefix: sorted(value, key=str) if all(not isinstance(x, (dict, list)) for x in value) else list(value)}
  return {prefix: value}

def _show(v) -> str:
  if v is None:
    return "not set"
  if isinstance(v, bool):
    return "yes" if v else "no"
  if isinstance(v, float) and v == int(v):
    return str(int(v))
  if isinstance(v, (list, dict)):
    return f"{len(v)} entr{'y' if len(v) == 1 else 'ies'}"
  return str(v)

def _drawing_name(d: dict) -> str:
  return (d.get("name") or d.get("id") or "a drawing") + (f" (revision {d['revision_label']})" if d.get("revision_label") else "")

def causes_of(run_a: dict, run_b: dict, drawings: dict) -> list:
  out: list = []
  ids_a, ids_b = [str(x) for x in run_a.get("drawing_revision_ids") or []], [str(x) for x in run_b.get("drawing_revision_ids") or []]
  only_a, only_b = [i for i in ids_a if i not in ids_b], [i for i in ids_b if i not in ids_a]
  group = lambda i: str((drawings.get(i) or {}).get("revision_group_id") or "")
  
  for i in list(only_b):
    twin = next((j for j in only_a if group(i) and group(j) == group(i)), None)
    if twin is not None:
      only_a.remove(twin)
      only_b.remove(i)
      da, db = drawings.get(twin) or {}, drawings.get(i) or {}
      out.append({"kind": "DRAWINGS", "text": f"{db.get('name') or da.get('name') or 'A drawing'}: revision {da.get('revision_label') or '(none named)'} was replaced by revision {db.get('revision_label') or '(none named)'}.",
        "detail": {"from": twin, "to": i}})
      
  for i in only_b:
    out.append({"kind": "DRAWINGS", "text": f"{_drawing_name(drawings.get(i) or {'id': i})} is measured in the later run and was not in the earlier one.", "detail": {"added": i}})
  for i in only_a:
    out.append({"kind": "DRAWINGS", "text": f"{_drawing_name(drawings.get(i) or {'id': i})} was measured in the earlier run and is not in the later one.", "detail": {"left_out": i}})
  fa, fb = _flatten(run_a.get("settings") or {}), _flatten(run_b.get("settings") or {})
  changed = [k for k in sorted(set(fa) | set(fb)) if fa.get(k) != fb.get(k)]
  for k in changed[:SETTINGS_CAP]:
    out.append({"kind": "SETTINGS", "text": f"Setting {k}: {_show(fa.get(k))}, then {_show(fb.get(k))}.", "detail": {"key": k, "a": fa.get(k), "b": fb.get(k)}})
  if len(changed) > SETTINGS_CAP:
    out.append({"kind": "SETTINGS", "text": f"{len(changed) - SETTINGS_CAP} more settings differ.", "detail": {"more": len(changed) - SETTINGS_CAP}})
  for kind, field, label in (("CONVENTION", "convention_code", "Measurement convention"), ("RULES", "rule_set_code", "Rule set"), ("ENGINE", "engine_version", "Engine version")):
    a, b = run_a.get(field), run_b.get(field)
    if a != b:
      out.append({"kind": kind, "text": f"{label}: {_show(a)}, then {_show(b)}.", "detail": {"a": a, "b": b}})
  return out

def _basis(item: dict) -> str:
  bits = [f"{s['level']} {s['delta']:+.2f}" for s in item["storeys"][:4]]
  more = len(item["storeys"]) - 4
  text = "; ".join(bits) + (f"; {more} more storey{'s' if more != 1 else ''}" if more > 0 else "")
  if item["members_changed"]:
    text += (". " if text else "") + f"{item['members_changed']} member{'s' if item['members_changed'] != 1 else ''} changed."
  return text

def variation_of(diff: dict, min_change_pct: float = MIN_CHANGE_PCT, causes: list | None = None, labels: dict | None = None) -> dict:
  lines, small = [], 0
  for i in diff["items"]:
    if i["status"] == "SAME":
      continue
    if i["status"] == "CHANGED" and i["pct"] is not None and abs(i["pct"]) < min_change_pct:
      small += 1
      continue
  
    kind = {"ADDED": "NEW_ITEM", "REMOVED": "ITEM_DROPPED"}.get(i["status"]) or ("ADDITION" if i["delta"] > 0 else "OMISSION")
    lines.append({"code": i["code"], "name": i["name"], "unit": i["unit"], "kind": kind, "previous": i["a"], "revised": i["b"], "addition": round(max(i["delta"], 0.0), 6),
      "omission": round(max(-i["delta"], 0.0), 6), "pct": i["pct"], "basis": _basis(i)})
  count = lambda k: sum(1 for l in lines if l["kind"] == k)
  return {"labels": labels or {}, "min_change_pct": min_change_pct, "lines": lines, "causes": causes or [],
    "counts": {"additions": count("ADDITION"), "omissions": count("OMISSION"), "new_items": count("NEW_ITEM"), "dropped_items": count("ITEM_DROPPED"),
      "unchanged": diff["measures"]["same"], "below_threshold": small},
    "note": "Quantities only. No rate has been applied; the value of each line is the quantity multiplied by the rate the contract gives for the item."}
