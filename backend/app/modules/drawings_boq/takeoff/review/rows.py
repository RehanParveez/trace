from __future__ import annotations
import re
from app.modules.drawings_boq.takeoff.run import completeness as RC
from app.modules.drawings_boq.takeoff.questions import keys as QK
from app.modules.drawings_boq.takeoff.questions import engine as QE
from app.modules.drawings_boq.takeoff.review import feeds as FD

AI_CANDIDATE, READING, CONFLICT, QUESTION = "AI_CANDIDATE", "READING", "CONFLICT", "QUESTION"
PRINTED, AI_READ, ASSUMED = "PRINTED", "AI_READ", "ASSUMED"
OPEN, DECIDED = "OPEN", "DECIDED"
READ = "READ"
ACCEPT, CORRECT, REJECT = "accept", "correct", "reject"
NOTE_TASK, SCHEDULE_TASK, LEGEND_TASK = "NOTE_FACT", "SCHEDULE_ROW", "LEGEND_ENTRY"
QUOTE_MEMBERS = 6
CANDIDATE_CROP = "/takeoff/candidates/{}/crop"
AI_CROP = "/takeoff/ai-shadow/{}/crop"
MEMBER_RX = re.compile(r"^p(\d+):")

def _action(action: str, value=None, choices: list | None = None) -> dict:
  return {"action": action, "value": value, "choices": list(choices or [])}

def place_of(member_id: str) -> tuple:
  m = MEMBER_RX.match(str(member_id))
  if m is None:
    return None, None
  n = int(m.group(1))
  return n // RC.SHEET_SHIFT, n % RC.SHEET_SHIFT

def lines_of(entries: list) -> list:
  out = []
  for e in entries:
    q = e.get("quantity") or {}
    out.append({"element": e["element"], "name": e["name"], "floor": e["floor"], "state": e["state"], "quantity": q.get("value"), "unit": q.get("unit"), "range": q.get("range")})
  return sorted(out, key=lambda r: (r["element"], r["floor"]))

def _by_element(ledger: list) -> dict:
  out: dict = {}
  for e in ledger:
    out.setdefault(e["element"], []).append(e)
  return out

def _union(*groups: list) -> list:
  seen, out = set(), []
  for group in groups:
    for e in group:
      if (e["element"], e["floor"]) not in seen:
        seen.add((e["element"], e["floor"]))
        out.append(e)
  return out

def _flagged(evidence: dict) -> dict:
  out: dict = {}
  for m in evidence.get("members") or []:
    if m["status"] != READ:
      out.setdefault(m["cls"], []).append(m)
  return out

def _decision(row: dict | None) -> dict | None:
  if not row:
    return None
  return {"action": row.get("action"), "value": row.get("value"), "by": row.get("by"), "at": row.get("at")}

def _answer_decision(answer: dict | None) -> dict | None:
  if not answer:
    return None
  value = answer.get("value")
  action = ACCEPT if value == QK.ACCEPT else REJECT if value in (QK.REJECT, QK.NOT_IN_SCOPE) else CORRECT
  return {"action": action, "value": value, "by": answer.get("by"), "at": answer.get("at")}

def _row(*, key: str, kind: str, item: str, prompt: str, source: str, entries: list, rates: dict | None, actions: list, decision: dict | None, floors: list | None = None,
    pages: list | None = None, crop_url: str | None = None, quote: str | None = None, money: float | None = None, extra: dict | None = None) -> dict:
  floors = floors if floors is not None else sorted({e["floor"] for e in entries if e["floor"] != "ALL"})
  pages = sorted({p for p in pages or [] if p is not None})
  unquantified = sum(1 for e in entries if not e.get("quantity"))
  return {"id": key, "key": key, "kind": kind, "item": item, "prompt": prompt, "floor": floors[0] if len(floors) == 1 else None, "floors": floors,
    "page": pages[0] if pages else None, "pages": pages, "crop_url": crop_url, "quote": quote, "source": source,
    "effect_rs": money if money is not None else QE.blocked_money(entries, rates), "lines": lines_of(entries), "unquantified": unquantified,
    "touches": sorted({e["element"] for e in entries}), "actions": actions, "state": DECIDED if decision else OPEN, "decision": decision, **(extra or {})}

def question_actions(q: dict) -> list:
  kind = q["kind"]
  if kind == QK.CONFIRM:
    return [_action(ACCEPT, QK.ACCEPT), _action(REJECT, QK.REJECT)]
  if kind == QK.SUPPLY:
    return [_action(REJECT, QK.NOT_IN_SCOPE)]
  
  out = []
  if q.get("default") and kind != QK.CONFLICT:
    out.append(_action(ACCEPT, str(q["default"]["value"])))
  out.append(_action(CORRECT, None, [o["value"] for o in q["options"]]))
  return out

def _stub(key: str, answer: dict | None) -> dict:
  return {"key": key, "kind": QK.CONFIRM, "prompt": "", "unit": None, "default": None, "options": [dict(o) for o in QE.OPTIONS[QK.CONFIRM]], "blocks": [], "floors": [], "members": 0,
    "entries": 0, "why": "", "money": None, "answer": answer, "state": QE.ANSWERED if answer else QE.OPEN}

def _reading_row(cls: str, members: list, q: dict, ledger: list, by_el: dict, crops: dict, rates: dict | None) -> dict:
  ids = {m["id"] for m in members}
  reached = [e for e in ledger if ids & set(e["members"])]
  asked = [e for el in q.get("blocks") or [] for e in by_el.get(el, [])]
  places = [place_of(m["id"]) for m in members]
  
  crop = next((crops[(p[0], p[1], str(m["mark"]).upper())] for p, m in zip(places, members) if m.get("mark") and (p[0], p[1], str(m["mark"]).upper()) in crops), None)
  quote = "; ".join(f"{m['mark'] or m['cls']}: {', '.join(m['reasons']) or m['status']}" for m in members[:QUOTE_MEMBERS]) + (f"; and {len(members) - QUOTE_MEMBERS} more" if len(members) > QUOTE_MEMBERS else "")
  label = cls.lower().replace("_", " ")
  return _row(key=q["key"], kind=READING, item=f"{len(members)} {label} reading(s) the reader was not sure of", prompt=q.get("prompt") or f"The reader was not sure of {len(members)} {label} member(s). Take the reading as it is, or leave them out?",
    source=PRINTED, entries=_union(reached, asked), rates=rates, actions=question_actions(q), decision=_answer_decision(q.get("answer")), pages=[p[1] for p in places],
    crop_url=CANDIDATE_CROP.format(crop) if crop else None, quote=quote or None, money=q.get("money"))

def _question_row(q: dict, by_el: dict, rates: dict | None) -> dict:
  kind = QUESTION if q["kind"] != QK.CONFLICT else CONFLICT
  entries = [e for el in q["blocks"] for e in by_el.get(el, [])]
  source = PRINTED if q["kind"] == QK.CONFLICT else ASSUMED
  return _row(key=q["key"], kind=kind, item=q["key"], prompt=q["prompt"], source=source, entries=entries, rates=rates, actions=question_actions(q), decision=_answer_decision(q.get("answer")),
    floors=q["floors"] or None, quote=q["why"], money=q.get("money"), extra={"default": q.get("default"), "unit": q.get("unit")})

def _note_rows(read: dict, review: dict, by_el: dict, rates: dict | None) -> list:
  out = []
  for n, f in enumerate((read["ai_value"] or {}).get("facts") or []):
    key = f"ai.{read['id']}.{n}"
    entries = [e for el in FD.note_items(f["key"]) for e in by_el.get(el, [])]
    text = f"{f['key']} {f['value']:g}" + (f" {f['unit']}" if f.get("unit") else "") + (f" ({f['scope']})" if f.get("scope") else "")
    out.append(_ai_row(key, text, read, f.get("quote"), entries, review, rates))
  return out

def _schedule_rows(read: dict, review: dict, by_el: dict, rates: dict | None) -> list:
  out = []
  for s in (read["ai_value"] or {}).get("schedules") or []:
    entries = [e for el in FD.schedule_items(s["kind"]) for e in by_el.get(el, [])]
    for n, r in enumerate(s["rows"]):
      key = f"ai.{read['id']}.{s['kind']}.{n}"
      cells = " ".join(str(r[f]) for f in ("mark", "floor", "size", "layer", "thickness") if r.get(f))
      out.append(_ai_row(key, f"{s['kind']} {cells}", read, r.get("quote"), entries, review, rates))
  return out

def _legend_rows(read: dict, review: dict, by_el: dict, rates: dict | None) -> list:
  out = []
  for n, r in enumerate((read["ai_value"] or {}).get("rows") or []):
    entries = [e for el in FD.legend_items(r["meaning"]) for e in by_el.get(el, [])]
    out.append(_ai_row(f"ai.{read['id']}.LEGEND.{n}", f"LEGEND {r['name']}: {r['meaning']}", read, r.get("quote"), entries, review, rates))
  return out

def _ai_row(key: str, text: str, read: dict, quote: str | None, entries: list, review: dict, rates: dict | None) -> dict:
  return _row(key=key, kind=AI_CANDIDATE, item=text, prompt=f"The AI read this from sheet {read['page_no']}. Take it, correct it, or leave it out?", source=AI_READ, entries=entries, rates=rates,
    actions=[_action(ACCEPT), _action(CORRECT), _action(REJECT)], decision=_decision(review.get(key)), pages=[read["page_no"]], crop_url=AI_CROP.format(read["id"]), quote=quote,
    extra={"read_id": str(read["id"]), "task": read["task"], "drawing_id": str(read["drawing_id"])})

def _fact_row(c: dict) -> dict:
  key = f"fact.{c['drawing_id']}.{c['id']}"
  options = [o["value"] for o in c["options"]]
  chosen = {"action": CORRECT, "value": c["chosen"], "by": None, "at": None} if c.get("chosen") else None
  return _row(key=key, kind=CONFLICT, item=c["title"], prompt=c["question"], source=PRINTED, entries=[], rates=None, actions=[_action(CORRECT, None, options)], decision=chosen,
    quote="; ".join(c["facts"]), extra={"affects": c.get("affects"), "drawing_id": str(c["drawing_id"]), "decision_id": c["id"]})

def order(row: dict) -> tuple:
  return (row["state"] != OPEN, -(row["effect_rs"] or 0.0), -len(row["touches"]), row["key"])

def build(*, ledger: list, questions: list, evidence: dict, reads: list, answers: dict, review: dict, crops: dict, rates: dict | None, facts: list | None = None) -> dict:
  by_el = _by_element(ledger)
  flagged = _flagged(evidence)
  rows, asks, seen = [], {}, set()
  
  for q in questions:
    if q["state"] == QE.RETIRED:
      continue
    asks[q["key"]] = q
    if q["kind"] == QK.CONFIRM:
      cls = q["key"].split(".", 1)[1]
      seen.add(cls)
      rows.append(_reading_row(cls, flagged.get(cls, []), q, ledger, by_el, crops, rates))
    else:
      rows.append(_question_row(q, by_el, rates))
      
  for cls, members in sorted(flagged.items()):
    if cls in seen:
      continue
    key = QK.reading_key(cls)
    asks[key] = _stub(key, answers.get(key))
    rows.append(_reading_row(cls, members, asks[key], ledger, by_el, crops, rates))
  for read in reads:
    if read["status"] != "OK" or not read.get("ai_value"):
      continue
    rows += _note_rows(read, review, by_el, rates) if read["task"] == NOTE_TASK else _schedule_rows(read, review, by_el, rates) if read["task"] == SCHEDULE_TASK else _legend_rows(read, review, by_el, rates) if read["task"] == LEGEND_TASK else []
  rows += [_fact_row(c) for c in facts or []]
  return {"rows": sorted(rows, key=order), "asks": asks}

def resolve(row: dict, ask: dict | None, action: str, value) -> tuple:
  spec = next((a for a in row["actions"] if a["action"] == action), None)
  if spec is None:
    return None, "This row does not take that action."
  given = spec["value"] if spec["value"] is not None else value
  if row["kind"] == AI_CANDIDATE:
    if action == CORRECT and not str(given or "").strip():
      return None, "Give the corrected value."
    return (None if action != CORRECT else str(given).strip()[:120]), None
  if given is None:
    return None, "Give the value."
  why = QE.check(ask, given) if ask is not None else (None if str(given) in spec["choices"] else "That is not one of the options.")
  return (None, why) if why else (str(given), None)

def changed(before: list, after: list) -> list:
  was = {(e["element"], e["floor"]): e for e in before}
  return sorted({e["element"] for e in after if was.get((e["element"], e["floor"])) != e} | {el for el, fl in was if (el, fl) not in {(e["element"], e["floor"]) for e in after}})
