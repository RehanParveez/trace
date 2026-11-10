from __future__ import annotations
import hashlib
import json
from app.modules.drawings_boq.takeoff.ai_reader import notes as NT
from app.engine.catalogue import note_keys as NK
from app.engine.measure import derived as DV
from app.modules.drawings_boq.takeoff.prep import facts as DF

FILE = "ai_money.json"
SUPPORTED = (NT.TASK,)
VIEW_KEYS = ("defined", "money_pkr", "within_pkr", "money_pct", "confirmed_items", "unpriced_items", "thin")

def parse(spec: str) -> tuple:
  task, _, variant = str(spec).partition(":")
  task = task.strip().upper()
  if task not in SUPPORTED:
    raise ValueError(f"The bench can run {', '.join(SUPPORTED)} with its cached answers on, not {task}.")
  return task, (variant.strip() or None)

def cached(folder: str, task: str, variant: str | None) -> dict:
  return NT.cached(folder, variant)

def tag_of(task: str, variant: str | None, notes: dict) -> str:
  body = json.dumps(notes, sort_keys=True, separators=(",", ":"), default=str)
  return f"ai-{task}-{variant or 'latest'}-{hashlib.sha256(body.encode('utf-8')).hexdigest()[:10]}"

def view_of(view: dict | None) -> dict | None:
  return None if view is None else {k: view.get(k) for k in VIEW_KEYS}

def items_of(rows: list, key: str) -> list:
  out = []
  for pdf, rs in rows:
    for r in rs:
      for it in r.get(key) or []:
        out.append({**it, "pdf": pdf, "page": r["page_no"]})
  return out

def rule_items_of(rows: list) -> list:
  sheets = [{"page_no": n * 10000 + r["page_no"], "label": None, "facts": r.get("facts"), "ai_facts": None} for n, (_pdf, rs) in enumerate(rows) for r in rs if r.get("facts") is not None]
  return DF.gather(sheets)["items"]

def input_lines(rows_on: list) -> list:
  out = []
  for it in items_of(rows_on, "ai_facts"):
    checks = it.get("checks") or []
    params = [{"param": p, "default": DV.PARAMS[p][0] if p in DV.PARAMS else None} for p in NT.fills_of(it)]
    out.append({"pdf": it["pdf"], "page": it["page"], "kind": it["kind"], "scope": it.get("scope"), "value_mm": it.get("value_mm"), "grade": it.get("grade"), "mix": it.get("mix"), "quote": it.get("quote"),
      "checks": [len([c for c in checks if c.get("passed")]), len(checks)], "sets": params})
  return out

def fill_of(rows_off: list, rows_on: list) -> dict:
  need = sorted(NT.missing(rule_items_of(rows_off)))
  filled = sorted({it["kind"] for it in items_of(rows_on, "ai_facts")} & set(need))
  return {"missing": need, "filled": filled}

def record(*, name: str, office: str, task: str, variant: str | None, off: dict | None, on: dict | None, rows_off: list, rows_on: list | None, pages: int) -> dict:
  return {"set": name, "office": office, "task": task, "variant": variant, "pages_cached": pages, "off": view_of(off), "on": view_of(on),
    "inputs": input_lines(rows_on) if rows_on is not None else [], "keys": fill_of(rows_off, rows_on) if rows_on is not None else {"missing": sorted(NT.missing(rule_items_of(rows_off))), "filled": []}}

def lines_for(records: list) -> list:
  if not records:
    return []
  out = ["## AI money: the same run with the cached answers off and on", "",
    "The run is the product run under the company's rules (the product run where there are none), read twice: once as it is, once with the accepted answers of the case's ai_cache as AI_READ inputs. Money accuracy is the Trace number within tolerance, valued at the rate book, over the confirmed money, as in the section above. An AI answer counts only if it passed every check; a tolerance is never changed here.", ""]
  head = ["Set", "Office", "Task", "Variant", "Cached pages", "Money accuracy off", "on", "Change", "Missing keys filled"]
  body = []
  
  for r in records:
    off, on = r["off"] or {}, r["on"] or {}
    a, b = off.get("money_pct"), on.get("money_pct")
    body.append([r["set"], r["office"], r["task"], r["variant"] or "latest", r["pages_cached"], "-" if a is None else f"{a:.1f}%", "-" if b is None else f"{b:.1f}%",
      "-" if a is None or b is None else f"{b - a:+.1f}", f"{len(r['keys']['filled'])} of {len(r['keys']['missing'])}"])
    
  out += ["| " + " | ".join(head) + " |", "|" + "|".join("---" for _ in head) + "|"] + ["| " + " | ".join(str(c) for c in row) + " |" for row in body] + [""]
  shown = [(r["set"], i) for r in records for i in r["inputs"]]
  if shown:
    out += ["AI-read inputs (AI_READ), with the checks each passed:", ""]
    for name, i in shown[:60]:
      value = i["value_mm"] if i["value_mm"] is not None else i["grade"] if i["grade"] is not None else i["mix"]
      sets = ", ".join(f"{p['param']} (otherwise {p['default']})" for p in i["sets"]) or "no engine parameter"
      out.append(f"- {name} {i['pdf']} page {i['page']}: {i['kind']} {i['scope'] or ''} = {value}; quote \"{str(i['quote'] or '')[:90]}\"; checks {i['checks'][0]} of {i['checks'][1]} passed; sets {sets}")
    out.append("")
  return out
