from __future__ import annotations
import argparse
import datetime
import hashlib
import json
import os
import re
import sys
import yaml
from app.engine.catalogue import loader as CL
from app.engine.catalogue import vocabulary as V
from app.modules.drawings_boq.takeoff.learning import pattern as PT, strip as ST
from app.modules.drawings_boq.takeoff.proof.answers import answers as AN

HERE = os.path.dirname(os.path.abspath(__file__))
SETTINGS = os.path.join(HERE, "miner.yaml")
PROPOSALS = os.path.join(os.path.dirname(HERE), "answers", "rule_proposals.yaml")
REGISTER_CONFUSION, AI_OVER_READ, AI_VALUE_FIX, VOCABULARY = "REGISTER_CONFUSION", "AI_OVER_READ", "AI_VALUE_FIX", "VOCABULARY"
PROPOSED, CONFIRMED, APPLIED, DECLINED = "PROPOSED", "CONFIRMED", "APPLIED", "DECLINED"
CHECKED, DRAFT = "CHECKED", "DRAFT"
TARGETS = {REGISTER_CONFUSION: "the rule that reads this field of a sheet's identity (extract/sheet_identity.py, prep/page_role.py)", AI_OVER_READ: "the check that lets this kind of AI read reach a review row (ai_reader/evidence.py)",
  AI_VALUE_FIX: "the prompt or the validator of this task (ai_reader/prompts, ai_reader/evidence.py)", VOCABULARY: "engine/catalogue/vocabulary.yaml, through the vocabulary review"}
HOW_TO = ("Each entry is a pattern that at least two sources showed in corrections people made. origin CHECKED means every line behind it was made by a person; DRAFT means some were made from draft truth for a dry run, and such an entry is never applied. "
  "replay says what the benchmark can tell: REMAP_SAFE or REMAP_UNSAFE for a register confusion, FITS or DOES_NOT_FIT for a vocabulary pair, NOT_REPLAYABLE for the rest. To take a proposal write confirmed: true, then run: "
  "python -m app.modules.drawings_boq.takeoff.proof.bench.miner apply --by <your name>. A vocabulary pair goes to the vocabulary review, where it is confirmed again; the other kinds are listed for you to change by hand.")

def settings() -> dict:
  with open(SETTINGS, encoding="utf-8") as fh:
    return yaml.safe_load(fh)

def read_records(paths: list) -> list:
  out: list = []
  for p in paths:
    with open(p, encoding="utf-8") as fh:
      out += [json.loads(line) for line in fh if line.strip()]
  return out

def write_records(path: str, records: list) -> None:
  with open(path, "w", encoding="utf-8", newline="\n") as fh:
    for r in records:
      fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")

def item_of_text(text) -> str | None:
  want = V.norm(text)
  if not want:
    return None
  for i in CL.items():
    if want in (V.norm(i.id), V.norm(i.name)):
      return i.id
  return V.item_for(text)

def keys_of(r: dict) -> list:
  if r.get("type") == "IDENTITY" and r.get("field") and r.get("from") and r.get("to"):
    return [(f"IDENTITY:{r['field']}:{r['from']}>{r['to']}", REGISTER_CONFUSION, f"A sheet whose {r['field']} is read as {r['from']} is set to {r['to']} by people.", {"field": r["field"], "from": r["from"], "to": r["to"]})]
  if r.get("type") != "REVIEW":
    return []
  
  task, subject, action = r.get("task"), r.get("subject") or "?", r.get("action")
  out = []
  
  if action == "reject" and r.get("reason"):
    out.append((f"REJECT:{task}:{subject}:{r['reason']}", AI_OVER_READ, f"AI reads of {subject} ({task}) are left out, reason {r['reason']}.", {}))
  if action == "correct" and task != PT.LEGEND_ENTRY and r.get("to") and r.get("from") != r.get("to"):
    out.append((f"FIX:{task}:{subject}:{r['from']}>{r['to']}", AI_VALUE_FIX, f"AI reads of {subject} ({task}) shaped '{r['from']}' are corrected to '{r['to']}'.", {}))
  if action == "correct" and task == PT.LEGEND_ENTRY and r.get("label") and r.get("to_text"):
    item = item_of_text(r["to_text"])
    if item:
      out.append((f"VOCAB:{V.norm(r['label'])}>{item}", VOCABULARY, f"The legend text '{r['label']}' is the catalogue item {item}.", {"label": r["label"], "item": item}))
  return out

def mine(records: list, cfg: dict | None = None) -> list:
  cfg = cfg or settings()
  groups: dict = {}
  
  for r in records:
    for key, kind, text, extra in keys_of(r):
      g = groups.setdefault(key, {"type": kind, "text": text, "extra": extra, "by_source": {}, "checked": 0, "n": 0})
      g["by_source"][r["source"]] = g["by_source"].get(r["source"], 0) + 1
      g["checked"] += 1 if r.get("checked", True) else 0
      g["n"] += 1
  out = []
  
  for key, g in sorted(groups.items()):
    top = max(g["by_source"].values())
    if len(g["by_source"]) < cfg["min_sources"] or g["n"] < cfg["min_count"] or top / g["n"] > cfg["max_top_share"]:
      continue
    out.append({"id": hashlib.sha256(key.encode("utf-8")).hexdigest()[:10], "key": key, "type": g["type"], "text": g["text"], **g["extra"], "records": g["n"], "sources": len(g["by_source"]),
      "by_source": dict(sorted(g["by_source"].items())), "origin": CHECKED if g["checked"] == g["n"] else DRAFT, "target": TARGETS[g["type"]], "replay": None, "status": PROPOSED, "confirmed": False, "confirmed_by": None, "date": None})
  return out

def load_doc(path: str = PROPOSALS) -> dict:
  doc = AN.read_yaml(path) or {}
  doc.setdefault("proposals", [])
  return doc

def save_doc(doc: dict, path: str = PROPOSALS) -> None:
  AN.write_yaml(path, {"how_to": HOW_TO, "proposals": doc["proposals"]})

def merge(doc: dict, found: list) -> dict:
  have = {p["key"]: p for p in doc["proposals"]}
  added = joined = 0
  for f in found:
    if f["key"] in have:
      old = have[f["key"]]
      old.update({k: f[k] for k in ("records", "sources", "by_source", "origin", "text")})
      joined += 1
    else:
      doc["proposals"].append(f)
      have[f["key"]] = f
      added += 1
  return {"added": added, "joined": joined}

def triples(score: dict) -> list:
  out = []
  for o in score.get("outcomes") or []:
    m = re.match(r"^(\w+): truth (.*), read (.*)$", o.get("detail") or "") if o.get("class") == "REGISTER" else None
    if m:
      out.append((o["set"], m.group(1), m.group(2), m.group(3), str(o.get("id", "")).split(":")[0]))
  return out

def replay_one(p: dict, score: dict | None, cfg: dict | None = None) -> dict:
  cfg = cfg or settings()
  
  if p["type"] == REGISTER_CONFUSION:
    if score is None:
      return {"verdict": "NOT_REPLAYABLE", "note": "no benchmark score was given"}
    got = [t for t in triples(score) if t[1] == p["field"] and t[3] == p["from"]]
    right = sum(1 for t in got if t[2] == p["to"])
    precision = right / len(got) if got else None
    return {"verdict": "NOT_REPLAYABLE" if precision is None else ("REMAP_SAFE" if precision >= cfg["replay_precision"] else "REMAP_UNSAFE"), "read_as_from": len(got), "truth_is_to": right,
      "precision": None if precision is None else round(precision, 3), "note": "the benchmark's truth is a draft no person has checked" + ("" if precision is None or precision >= cfg["replay_precision"] else "; reading it as '" + p["from"] + "' is right more often than not, so a plain remap would do harm and the rule needs a cue")}
    
  if p["type"] == VOCABULARY:
    have = {i.id for i in CL.items()}
    bad = []
    
    if p["item"] not in have:
      bad.append(f"{p['item']} is not a catalogue item")
    if V.item_for(p["label"]):
      bad.append("the vocabulary already has this text")
    bad += [b for b in V.problems({"entries": [*V.entries(), {"text": p["label"], "item": p["item"], "confirmed_by": "x", "date": "x"}]}) if p["label"] in b]
    return {"verdict": "DOES_NOT_FIT" if bad else "FITS", "note": "; ".join(bad) or "the pair is new and the vocabulary takes it"}
  return {"verdict": "NOT_REPLAYABLE", "note": "judging this needs a model's cached answers on a set and checked truth; neither exists yet"}

def replay(doc: dict, score: dict | None) -> int:
  for p in doc["proposals"]:
    p["replay"] = replay_one(p, score)
  return len(doc["proposals"])

def dry_records(score: dict, cases_dir: str | None = None) -> list:
  from app.modules.drawings_boq.takeoff.proof.reading import sets as S
  office_of_key = {ref.pdf_key: ref.office for ref in S.find_sets(cases_dir)}
  out = []
  
  for _alias, field, truth, read, key in triples(score):
    if field not in ST.IDENTITY_FIELDS or read in ("None", "") or truth in ("None", "") or read == truth:
      continue
    office = office_of_key.get(key, S.UNKNOWN_OFFICE)
    out.append({"source": office, "type": "IDENTITY", "field": field, "from": ST.clean(read), "to": ST.clean(truth), "checked": False})
  return out

def apply(doc: dict, by: str, today: str) -> dict:
  from app.modules.drawings_boq.takeoff.proof import vocabulary as VR
  review = VR.load_review()
  moved, by_hand, refused = 0, [], []
  for p in doc["proposals"]:
    if not p["confirmed"] or p["status"] in (APPLIED, DECLINED):
      continue
    
    if p["origin"] != CHECKED:
      refused.append(f"{p['key']}: some of its lines were made from draft truth, not by a person")
      continue
    if p["type"] == VOCABULARY:
      if (p.get("replay") or {}).get("verdict") != "FITS":
        refused.append(f"{p['key']}: replay it first; it must fit the vocabulary")
        continue
      
      VR.merge(review, [{"text": p["label"], "match": p["label"], "scope": VR.GENERAL, "qs": None, "unit": None, "source": "CORRECTIONS", "count": p["records"], "where": [f"{p['sources']} sources"]}])
      entry = next((e for e in review["entries"] if e["key"] == VR.entry_key(VR.GENERAL, None, p["label"])), None)
      if entry is not None:
        entry["item"] = p["item"]
      p["status"] = APPLIED
      moved += 1
    else:
      p["status"] = CONFIRMED
      by_hand.append(f"{p['key']}: change {p['target']}")
    p["confirmed_by"], p["date"] = by, today
  if moved:
    VR.save_review(review)
  return {"moved_to_vocabulary_review": moved, "by_hand": by_hand, "refused": refused}

def lines(doc: dict) -> list:
  ps = doc["proposals"]
  out = [f"{len(ps)} proposal(s): " + ", ".join(f"{k} {sum(1 for p in ps if p['status'] == k)}" for k in (PROPOSED, CONFIRMED, APPLIED, DECLINED)) + f"; {sum(1 for p in ps if p['origin'] == CHECKED)} from checked lines, {sum(1 for p in ps if p['origin'] == DRAFT)} from draft lines"]
  for p in ps:
    r = p.get("replay") or {}
    out.append(f"  [{p['status']}] {p['type']} {p['key']}  {p['records']} line(s), {p['sources']} source(s), {p['origin']}, replay {r.get('verdict', 'not run')}")
  return out

def export(out: str, salt: str) -> int:
  import asyncio
  from app.core.database import AsyncSessionLocal
  from app.modules.drawings_boq.takeoff.learning import service as LS

  async def run():
    async with AsyncSessionLocal() as session:
      return await LS.export_shared(session, salt)
  records = asyncio.run(run())
  write_records(out, records)
  return len(records)

def main(argv: list | None = None) -> int:
  ap = argparse.ArgumentParser(description="Turn corrections that several sources made into rule proposals, try them on the benchmark, and apply the ones a person confirmed.")
  sub = ap.add_subparsers(dest="cmd", required=True)
  e = sub.add_parser("export", help="write the stripped corrections of the companies that chose SHARED")
  e.add_argument("--out", required=True)
  e.add_argument("--salt", required=True, help="a secret kept by whoever runs this; the same salt gives the same number for a company")
  d = sub.add_parser("dry-records", help="make lines from a reading score's draft truth, for a dry run; none can be confirmed or applied")
  d.add_argument("--score", required=True, help="reading_score.json")
  d.add_argument("--out", required=True)
  d.add_argument("--cases-dir", default=None)
  m = sub.add_parser("mine")
  
  m.add_argument("files", nargs="+")
  m.add_argument("--file", default=PROPOSALS, help="the proposals file")
  r = sub.add_parser("replay")
  r.add_argument("--score", help="reading_score.json")
  r.add_argument("--file", default=PROPOSALS)
  a = sub.add_parser("apply")
  a.add_argument("--by", required=True)
  a.add_argument("--file", default=PROPOSALS)
  l = sub.add_parser("list")
  l.add_argument("--file", default=PROPOSALS)
  args = ap.parse_args(argv)
  
  if args.cmd == "export":
    print(f"{export(args.out, args.salt)} line(s) written")
    return 0
  if args.cmd == "dry-records":
    with open(args.score, encoding="utf-8") as fh:
      recs = dry_records(json.load(fh), args.cases_dir)
    write_records(args.out, recs)
    print(f"{len(recs)} draft line(s) written; none is checked")
    return 0
  
  doc = load_doc(args.file)
  if args.cmd == "mine":
    r = merge(doc, mine(read_records(args.files)))
    print(f"{r['added']} new, {r['joined']} seen again")
    save_doc(doc, args.file)
  elif args.cmd == "replay":
    score = None
    if args.score:
      with open(args.score, encoding="utf-8") as fh:
        score = json.load(fh)
    print(f"{replay(doc, score)} replayed")
    save_doc(doc, args.file)
    
  elif args.cmd == "apply":
    res = apply(doc, args.by, datetime.date.today().isoformat())
    print(f"{res['moved_to_vocabulary_review']} to the vocabulary review")
    for h in res["by_hand"]:
      print("  by hand: " + h)
    for x in res["refused"]:
      print("  refused: " + x, file=sys.stderr)
    save_doc(doc, args.file)
    return 0 if not res["refused"] else 1
  
  for ln in lines(doc):
    print(ln)
  return 0

if __name__ == "__main__":
  sys.exit(main())
