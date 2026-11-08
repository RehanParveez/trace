from __future__ import annotations
import os
from app.modules.drawings_boq.takeoff.proof.reading import score as SCR
import yaml
from app.engine.measure import rule_registry as RR
from app.modules.drawings_boq.takeoff.proof.bench import sets as BS
from app.modules.drawings_boq.takeoff.proof.reading import sets as S
from app.modules.drawings_boq.takeoff.proof.reading import formats as F
from app.modules.drawings_boq.takeoff.proof.reading import settings as ST
import re
import json

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(HERE, "evidence.yaml")
PACK = "GX-2"
OWNED_PACKS = ("GX-1", "GX-2")
MATCHED = (SCR.OK, SCR.WRONG)
TRUTH = (SCR.OK, SCR.WRONG, SCR.MISSED_S, SCR.MISSED_R)
JUDGED = (SCR.TRUE, SCR.INV_S, SCR.INV_F)

def load_config(path: str = CONFIG) -> dict:
  with open(path, encoding="utf-8") as fh:
    return yaml.safe_load(fh) or {}

def reading_rules(rules: list | None = None) -> list:
  return [r for r in (RR.rules() if rules is None else rules) if r.get("kind") == "READING" and r.get("class")]

def office_of_alias(cases_dir: str | None, root: str) -> dict:
  offices = BS.load().get("sets") or {}
  out: dict = {}
  for ref in S.find_sets(cases_dir, root):
    if ref.link:
      continue
    row = offices.get(ref.case) or {}
    out[F.load_set(ref.truth_folder).document.alias] = row.get("office") or "?"
  return out

def tally(outcomes: list, offices: dict, held_out: list) -> dict:
  evidence: dict = {}
  held: dict = {}
  for o in outcomes:
    if o["set"] in held_out:
      key, into = (o["set"], o["class"]), held
    else:
      key, into = (offices.get(o["set"], "?"), o["class"]), evidence
    slot = into.setdefault(key, {"counts": {}, "sets": set()})
    slot["counts"][o["outcome"]] = slot["counts"].get(o["outcome"], 0) + 1
    if o["outcome"] in TRUTH:
      slot["sets"].add(o["set"])
  return {"evidence": evidence, "held_out": held}

def rates(slot: dict) -> dict:
  c = slot["counts"]
  truth = sum(c.get(k, 0) for k in TRUTH)
  matched = sum(c.get(k, 0) for k in MATCHED)
  judged = sum(c.get(k, 0) for k in JUDGED)
  right = c.get(SCR.OK, 0)
  return {"truth": truth, "matched": matched, "right": right, "judged": judged, "true": c.get(SCR.TRUE, 0), "sets": len(slot["sets"]),
    "recall": None if not truth else matched / truth, "precision": None if not judged else c.get(SCR.TRUE, 0) / judged, "accuracy": None if not matched else right / matched}

def meets(rule: dict, on: dict) -> bool:
  return all(on[k] is not None and on[k] >= rule[k] for k in ("recall", "precision", "accuracy"))

def rows_of(rule: dict, on_tally: dict, off_tally: dict) -> list:
  rows = []
  for (office, cls), slot in sorted(on_tally.items()):
    if cls != rule["class"] or office == "?":
      continue
    on = rates(slot)
    off = rates(off_tally.get((office, cls)) or {"counts": {}, "sets": set()})
    if not on["truth"]:
      continue
    metric = (f"reading score, class {cls}, every reading rule on: matched {on['matched']} of {on['truth']} (right value {on['right']}), true {on['true']} of {on['judged']} read; off: matched {off['matched']} of {off['truth']}")
    rows.append({"office": office, "sets": on["sets"], "metric": metric, "value": on["right"], "pack": PACK, "met": meets(rule, on)})
  return rows

def unseen_rows(rule: dict, held_on: dict, offices: dict, min_truth: int) -> list:
  rows = []
  for (name, cls), slot in sorted(held_on.items()):
    if cls != rule["class"]:
      continue
    on = rates(slot)
    if on["truth"] < min_truth:
      continue
    metric = f"unseen set {name}, reading score, class {cls}, every reading rule on: matched {on['matched']} of {on['truth']} (right value {on['right']}), true {on['true']} of {on['judged']} read"
    rows.append({"office": offices.get(name, "?"), "sets": 1, "unseen": True, "metric": metric, "value": on["right"], "pack": PACK, "met": meets(rule, on)})
  return rows

def run(cases_dir: str | None, root: str, score_dir: str | None = None) -> dict:
  ids = [r["id"] for r in RR.rules() if r["kind"] == "READING"]
  offices = office_of_alias(cases_dir, root)
  held_out = load_config().get("held_out") or []
  
  off = SCR.run("all", cases_dir, score_dir, root, overrides={i: False for i in ids})
  on = SCR.run("all", cases_dir, score_dir, root, overrides={i: True for i in ids})
  redraft = sorted(s["alias"] for s in on["sets"] if (s.get("truth_quality") or {}).get("status") == "REDRAFT")
  off["outcomes"] = [o for o in off["outcomes"] if o["set"] not in redraft]
  on["outcomes"] = [o for o in on["outcomes"] if o["set"] not in redraft]
  off_t, on_t = tally(off["outcomes"], offices, held_out), tally(on["outcomes"], offices, held_out)
  rules = reading_rules()
  evidence = {r["id"]: rows_of(r, on_t["evidence"], off_t["evidence"]) + unseen_rows(r, on_t["held_out"], offices, ST.unseen_min_truth()) for r in rules}
  held = []
  for (name, cls), slot in sorted(on_t["held_out"].items()):
    a, b = rates(slot), rates(off_t["held_out"].get((name, cls)) or {"counts": {}, "sets": set()})
    if a["truth"]:
      held.append({"set": name, "class": cls, "truth": a["truth"], "matched_on": a["matched"], "right_on": a["right"], "judged_on": a["judged"], "true_on": a["true"], "matched_off": b["matched"]})
  return {"evidence": evidence, "held_out": held, "redraft": redraft, "hash_on": on["hash"], "hash_off": off["hash"]}

def verdicts(rules: list, evidence: dict) -> dict:
  out = {}
  for r in rules:
    met = sorted({row["office"] for row in evidence.get(r["id"], []) if row["met"] and not row.get("unseen")})
    unseen = any(row["met"] and row.get("unseen") for row in evidence.get(r["id"], []))
    out[r["id"]] = {"offices": met, "unseen": unseen, "general": len(met) >= RR.MIN_OFFICES and unseen}
  return out

def block_bounds(lines: list, rule_id: str) -> tuple:
  start = next(i for i, ln in enumerate(lines) if ln.strip() == f"- id: {rule_id}")
  end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("- id: ")), len(lines))
  return start, end

def row_text(row: dict) -> str:
  return f"    - {{office: {row['office']}, sets: {row['sets']}, {'unseen: true, ' if row.get('unseen') else ''}metric: \"{row['metric']}\", value: {row['value']}, pack: {row['pack']}, met: {'true' if row['met'] else 'false'}}}"

def write_registry(path: str, evidence: dict, verdict: dict) -> list:
  with open(path, encoding="utf-8", newline="") as fh:
    raw = fh.read()
  newline = "\r\n" if "\r\n" in raw else "\n"
  lines = raw.replace("\r\n", "\n").split("\n")
  promoted = []
  
  for rule_id, rows in evidence.items():
    start, end = block_bounds(lines, rule_id)
    block = [ln for ln in lines[start:end] if not any(re.search(rf"pack: {p}[,}}]", ln) for p in OWNED_PACKS)]
    block = ["  evidence:" if ln == "  evidence: []" else ln for ln in block]
    at = next(i for i, ln in enumerate(block) if ln.startswith("  notes:"))
    block[at:at] = [row_text(r) for r in rows]
    if not any(ln == "  evidence:" for ln in block):
      raise ValueError(f"{rule_id} needs an evidence list written one row per line")

    if verdict[rule_id]["general"] and any(ln == "  status: CANDIDATE" for ln in block):
      block = ["  status: GENERAL" if ln == "  status: CANDIDATE" else ("  default: on" if ln == "  default: off" else ln) for ln in block]
      promoted.append(rule_id)
    lines[start:end] = block
  with open(path, "w", encoding="utf-8", newline="") as fh:
    fh.write(newline.join(lines))
  RR.reload()
  return promoted

def demote_registry(path: str, ids: list) -> list:
  with open(path, encoding="utf-8", newline="") as fh:
    raw = fh.read()
  newline = "\r\n" if "\r\n" in raw else "\n"
  lines = raw.replace("\r\n", "\n").split("\n")
  done = []
  for rule_id in ids:
    start, end = block_bounds(lines, rule_id)
    block = lines[start:end]
    if any(ln == "  status: GENERAL" for ln in block):
      lines[start:end] = ["  status: CANDIDATE" if ln == "  status: GENERAL" else ("  default: off" if ln == "  default: on" else ln) for ln in block]
      done.append(rule_id)
  with open(path, "w", encoding="utf-8", newline="") as fh:
    fh.write(newline.join(lines))
  RR.reload()
  return done

def render(result: dict, rules: list, verdict: dict) -> str:
  L = ["# Rule evidence from the reading score", "", "A row is one office. A rule meets its metric on an office when recall, precision and value accuracy are all at or above its thresholds, scored with every reading rule on.", ""]
  L += ["| Rule | Class | Office | Sets | Matched | Truth | Right value | Judged | True | Met |", "|---|---|---|---|---|---|---|---|---|---|"]
  for r in rules:
    for row in result["evidence"][r["id"]]:
      m = re.search(r"matched (\d+) of (\d+) \(right value (\d+)\), true (\d+) of (\d+)", row["metric"])
      L.append(f"| {r['id']} | {r['class']} | {row['office']} | {row['sets']} | {m.group(1)} | {m.group(2)} | {m.group(3)} | {m.group(5)} | {m.group(4)} | {'yes' if row['met'] else 'no'} |")
  L += ["", "## Verdicts", "", "A rule is GENERAL when two offices meet its metric and a held-out set, which no pack opened, meets it too.", "", "| Rule | Offices that meet | Unseen set meets | Status |", "|---|---|---|---|"]
  for r in rules:
    v = verdict[r["id"]]
    L.append(f"| {r['id']} | {', '.join(v['offices']) or 'none'} | {'yes' if v['unseen'] else 'no'} | {'GENERAL, on by default' if v['general'] else 'stays CANDIDATE'} |")
  gap = [r["id"] for r in rules if r["status"] == "GENERAL" and not verdict[r["id"]]["unseen"]]
  L += ["", "## GENERAL rules that fail the unseen-set test", "", "A GENERAL rule needs a held-out set whose class meets the rule's thresholds. These have none, so `reading evidence --write --demote` would send them back to CANDIDATE and off, evidence kept: " + (", ".join(gap) or "none") + "."]
  L += ["", "## Held-out sets (reported, never counted)","", "| Set | Class | Truth | Matched on | Right value | Judged | True | Matched off |", "|---|---|---|---|---|---|---|---|"]
  for h in result["held_out"]:
    L.append(f"| {h['set']} | {h['class']} | {h['truth']} | {h['matched_on']} | {h['right_on']} | {h['judged_on']} | {h['true_on']} | {h['matched_off']} |")
  L += ["", "Left out of the evidence because their truth sample was more than the allowed share wrong (REDRAFT): " + (", ".join(result.get("redraft") or []) or "none") + "."]
  L += ["", f"Reading hash with every rule on `{result['hash_on'][:16]}`, with every rule off `{result['hash_off'][:16]}`.", ""]
  return "\n".join(L)

def cmd_evidence(args) -> int:
  result = run(args.cases_dir, args.root, args.score_dir)
  rules = reading_rules()
  verdict = verdicts(rules, result["evidence"])
  os.makedirs(args.out, exist_ok=True)
  with open(os.path.join(args.out, "evidence.json"), "w", encoding="utf-8", newline="\n") as fh:
    json.dump(result, fh, indent=1, sort_keys=True)
  with open(os.path.join(args.out, "evidence.md"), "w", encoding="utf-8", newline="\n") as fh:
    fh.write(render(result, rules, verdict))
  for r in rules:
    v = verdict[r["id"]]
    
    print(f"{r['id']}: meets on {', '.join(v['offices']) or 'no office'}{' -> GENERAL' if v['general'] else ''}")
  gap = [r["id"] for r in rules if r["status"] == "GENERAL" and not verdict[r["id"]]["unseen"]]
  print(f"{len(gap)} GENERAL rule(s) have no unseen set that meets their metric: {', '.join(gap) or 'none'}")
  if args.write:
    promoted = write_registry(RR.PATH, result["evidence"], verdict)
    print(f"registry updated; {len(promoted)} rule(s) now GENERAL and on: {', '.join(promoted) or 'none'}")
    if getattr(args, "demote", False) and gap:
      sent = demote_registry(RR.PATH, gap)
      print(f"{len(sent)} rule(s) sent back to CANDIDATE and off, evidence kept: {', '.join(sent)}. Engine hashes of the cases that used them move; read the new score before you re-pin anything.")

    bad = RR.problems(RR.load())
    for b in bad:
      print(b)
    return 1 if bad else 0
  return 0
