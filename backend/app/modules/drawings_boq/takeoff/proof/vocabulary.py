from __future__ import annotations
import os
from app.modules.drawings_boq.takeoff.proof.answers import answers as AN
from app.engine.catalogue import vocabulary as V
from app.modules.drawings_boq.takeoff.proof.answers import qs_map as QM
from app.modules.drawings_boq.takeoff.proof.answers import qs_import as QI
from app.modules.drawings_boq.takeoff.proof import case_io as CIO
from app.modules.drawings_boq.takeoff.extract import electrical as EL
from app.modules.drawings_boq.takeoff.extract import electrical_rules as ER
from app.modules.drawings_boq.takeoff.ai_reader import cache as CACHE
from app.modules.drawings_boq.takeoff.ai_reader import prompts as PR
from app.modules.drawings_boq.takeoff.ai_reader import evidence as EV
import asyncio
from app.engine.catalogue import loader as CL
import argparse
import sys
import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
REVIEW_PATH = os.path.join(HERE, "answers", "vocabulary_review.yaml")
PROMPT_NAME = "vocab.v1"
GENERAL, QS = "GENERAL", "QS"
LEGEND_LABEL, QS_LINE = "LEGEND_LABEL", "QS_LINE"
NEAREST = 5
MAX_WHERE = 5
HOW_TO = ("Each entry is a label or a line of a bill that matched no catalogue item. proposal is what a model suggested from the five nearest items in choices. To accept a pair write confirmed: true, "
  "and item: with the catalogue id when you are not taking the proposal. Write confirmed: true and skip: true when the text is not a catalogue item. Scope GENERAL moves the pair to "
  "engine/catalogue/vocabulary.yaml for every company; scope QS moves it to the QS map of that QS only, which is where one QS's private shorthand belongs. A proposal alone never moves. "
  "Then run: python -m app.modules.drawings_boq.takeoff.proof.vocabulary confirm --by <your name>.")

def load_review() -> dict:
  doc = AN.read_yaml(REVIEW_PATH) or {}
  doc.setdefault("entries", [])
  doc.setdefault("declined", [])
  return doc

def save_review(doc: dict) -> None:
  AN.write_yaml(REVIEW_PATH, {"how_to": HOW_TO, "entries": doc["entries"], "declined": sorted(set(doc["declined"]))})

def entry_key(scope: str, qs: str | None, text: str) -> str:
  return f"{qs}:{V.norm(text)}" if scope == QS else V.norm(text)

def merge(doc: dict, found: list) -> dict:
  known = {e["key"]: e for e in doc["entries"]}
  added = joined = left = 0
  
  for f in found:
    key = entry_key(f["scope"], f.get("qs"), f["match"])
    if V.item_for(f["match"]) or key in doc["declined"]:
      left += 1
      continue
    if key in known:
      e = known[key]
      e["count"] += f["count"]
      e["sources"] = sorted(set(e["sources"]) | {f["source"]})
      e["where"] = (e["where"] + [w for w in f["where"] if w not in e["where"]])[:MAX_WHERE]
      joined += 1
      continue
    known[key] = {"key": key, "text": f["text"], "match": f["match"], "scope": f["scope"], "qs": f.get("qs"), "unit": f.get("unit"), "sources": [f["source"]], "count": f["count"],
      "where": f["where"][:MAX_WHERE], "choices": None, "proposal": None, "confirmed": False, "item": None, "skip": False}
    doc["entries"].append(known[key])
    added += 1
  return {"added": added, "joined": joined, "left_out": left}

def qs_unknowns(case_name: str, cases_dir: str | None) -> tuple:
  case, path, block_floor = QI.case_workbook(case_name, cases_dir)
  if not os.path.isfile(path):
    return [], {}
  
  paths = QM.case_paths(case_name, cases_dir)
  qs_id = (AN.read_yaml(paths["review"]) or {}).get("qs") or case_name
  vocab = QI.vocabulary()
  imp = QI.read_workbook(path, block_floor, vocab)
  built = QM.build(imp, QM.load_map()["qs"].get(qs_id) or {}, QM.Index(vocab), QM.read_ai(paths["folder"]), qs_id, case_name)
  found = [{"text": r["qs_line"], "match": r["key"], "scope": QS, "qs": qs_id, "unit": next(iter(r["quantity"]), None), "source": QS_LINE, "count": r["rows"],
    "where": [f"workbook {imp['sha256'][:8]} sheet {sheet}" for sheet in r["sheets"]]} for r in built["reviews"] if r["element"] is None]
  return found, QM.percentages(built["items"], built["unmapped_lines"], imp)

def legend_unknowns(case_name: str, files_dir: str | None) -> list:
  from app.modules.drawings_boq.takeoff.run import reader as RDR
  case = CIO.load_case(os.path.join(CIO.HERE, case_name))
  files, _problems = CIO.find_files(case, files_dir)
  out = []
  
  for name, path in files.items():
    with open(path, "rb") as fh:
      data = fh.read()
    doc, analysed, _p = RDR.analyse_pdf(data, None)
    for no, a in sorted(analysed.items()):
      for r in a.meta.get("electrical_legend") or []:
        if EL.kind_of(r["name"]) == ER.OTHER:
          out.append({"text": r["name"], "match": r["name"], "scope": GENERAL, "qs": None, "unit": "nos", "source": LEGEND_LABEL, "count": 1, "where": [f"pdf {CACHE.pdf_sha256(data)[:8]} page {no}"]})
    try:
      doc.close()
    except Exception:
      pass
  return out

def nearest(index: QM.Index, text: str, unit, n: int = NEAREST) -> list:
  want = index.want_of(text, unit)
  scored = [(len(want & index.names[i.id]), len(index.names[i.id]), index.order[i.id], i.id) for i in index.items]
  return [i for hit, _len, _order, i in sorted((s for s in scored if s[0] > 0), key=lambda s: (-s[0], s[1], s[2]))][:n]

async def propose_one(entry: dict, index: QM.Index, ask, model: str) -> dict:
  entry["choices"] = nearest(index, entry["text"], entry.get("unit"))
  if not entry["choices"]:
    entry["proposal"] = None
    return entry
  
  listing = "\n".join(f"{i} | {index.by_id[i].name} | {index.by_id[i].unit}" for i in entry["choices"])
  parsed = await ask(PR.render(PROMPT_NAME, line=entry["text"], unit=str(entry.get("unit") or "?"), choices=listing))
  answer = parsed if isinstance(parsed, dict) else {}
  element, reason = answer.get("element"), str(answer.get("reason") or "").strip()
  checks = [EV.choice_offered(element, entry["choices"]), EV.result("reason_given", bool(reason), "a reason is given" if reason else "no reason is given")]
  entry["proposal"] = {"element": element if EV.passed(checks) else None, "reason": reason, "model": model, "checks": [c["name"] for c in checks if not c["passed"]]}
  return entry

def propose(doc: dict, index: QM.Index, ask, model: str, force: bool) -> dict:
  todo = [e for e in doc["entries"] if force or (e["proposal"] is None and e["choices"] is None)]

  async def run():
    for e in todo:
      await propose_one(e, index, ask, model)
  asyncio.run(run())
  return {"asked": sum(1 for e in todo if e["choices"]), "no_near_item": sum(1 for e in todo if not e["choices"]), "none_chosen": sum(1 for e in todo if e["proposal"] and not e["proposal"]["element"])}

def confirm(doc: dict, by: str, today: str, map_path: str = QM.MAP_PATH) -> dict:
  have = {i.id for i in CL.items()}
  data, qs_data = {"entries": list(V.entries())}, QM.load_map(map_path)
  kept, moved, refused = [], 0, []
  for e in doc["entries"]:
    if not e["confirmed"]:
      kept.append(e)
      continue
    
    item = e.get("item") or (e.get("proposal") or {}).get("element")
    if e["skip"]:
      if e["scope"] == QS:
        qs_data["qs"].setdefault(e["qs"], {})[e["match"]] = {"skip": True, "note": "marked not a catalogue item in the vocabulary review"}
      else:
        doc["declined"].append(e["key"])
      moved += 1
      continue
    if not item or item not in have:
      refused.append(f"{e['text']}: {item!r} is not a catalogue item")
      kept.append(e)
      continue
    if e["scope"] == QS:
      qs_data["qs"].setdefault(e["qs"], {})[e["match"]] = {"element": item}
    elif V.item_for(e["match"]):
      refused.append(f"{e['text']}: the vocabulary already has this text")
      kept.append(e)
      continue
    
    else:
      row = {"text": e["match"], "item": item, "confirmed_by": by, "date": today}
      bad = V.problems({"entries": [*data["entries"], row]})
      if bad:
        refused.append(f"{e['text']}: {bad[-1].split(': ', 1)[-1]}; keep a long line in the QS map")
        kept.append(e)
        continue
      data["entries"].append(row)
    moved += 1
  V.save(data)
  QM.save_map(qs_data, map_path)
  doc["entries"] = kept
  return {"moved": moved, "refused": refused, "left": len(kept)}

def lines(doc: dict) -> list:
  entries = doc["entries"]
  listed = [e for e in entries if e["choices"] == []]
  return [f"{len(entries)} unknown(s) waiting: {sum(1 for e in entries if e['proposal'] and e['proposal']['element'])} with a proposal, {sum(1 for e in entries if e['confirmed'])} marked confirmed, "
    f"{sum(1 for e in entries if e['choices'] is None)} not yet offered to a model; {len(listed)} listed with no near catalogue item; {len(doc['declined'])} declined",
    *[f"  listed: {e['text']} ({e['scope']}, {e['count']} time(s))" for e in listed[:40]]]

def main(argv: list | None = None) -> int:
  ap = argparse.ArgumentParser(description="Collect labels and bill lines that matched no catalogue item, propose a catalogue item for each, and move only the pairs you confirmed to the vocabulary or the QS map.")
  sub = ap.add_subparsers(dest="cmd", required=True)
  c = sub.add_parser("collect")
  c.add_argument("cases", nargs="*", help="case names (default: every case folder)")
  c.add_argument("--cases-dir", default=None)
  c.add_argument("--no-pdf", action="store_true", help="skip reading the PDFs for legend labels")
  c.add_argument("--no-qs", action="store_true", help="skip the QS workbooks")
  p = sub.add_parser("propose")
  p.add_argument("--where", choices=("local", "outside"), required=True, help="local uses Ollama; outside uses the Anthropic API with AI_API_KEY")
  p.add_argument("--model", default=None)
  p.add_argument("--force", action="store_true")
  k = sub.add_parser("confirm")
  k.add_argument("--by", required=True, help="who confirmed the pairs; written to vocabulary.yaml")
  sub.add_parser("report")
  args = ap.parse_args(argv)
  doc = load_review()
  
  if args.cmd == "collect":
    for name in args.cases or CIO.list_cases():
      found = []
      if not args.no_qs:
        try:
          got, shares = qs_unknowns(name, args.cases_dir)
          found += got
          if shares:
            print(f"{name}: QS rows by how mapped: " + ", ".join(f"{k} {v}" for k, v in shares.items()))
        except (FileNotFoundError, ValueError, KeyError) as exc:
          print(f"{name}: QS lines not read: {exc}", file=sys.stderr)
      if not args.no_pdf:
        try:
          found += legend_unknowns(name, CIO.cases_dir(args.cases_dir))
        except Exception as exc:
          print(f"{name}: legend labels not read: {type(exc).__name__}: {exc}", file=sys.stderr)
      r = merge(doc, found)
      print(f"{name}: {r['added']} new, {r['joined']} seen again, {r['left_out']} already settled")
    save_review(doc)
    
  elif args.cmd == "propose":
    from app.modules.ai_requests.service import AIOrchestratorService, CONSENT_PROVIDER, DEFAULT_MAX_TOKENS, model_of
    provider = CONSENT_PROVIDER["LOCAL" if args.where == "local" else "OUTSIDE"]
    model = args.model or model_of(provider)

    async def ask(prompt: str):
      _raw, parsed, _usage = await AIOrchestratorService._call_provider(provider, model, prompt, [], DEFAULT_MAX_TOKENS, None)
      return parsed
    r = propose(doc, QM.Index(QI.vocabulary()), ask, model, args.force)
    print(f"{r['asked']} asked, {r['no_near_item']} listed with no near item, {r['none_chosen']} where the model chose none")
    save_review(doc)
    
  elif args.cmd == "confirm":
    r = confirm(doc, args.by, datetime.date.today().isoformat())
    print(f"{r['moved']} pair(s) moved, {r['left']} left in the review")
    for why in r["refused"]:
      print(f"  refused: {why}", file=sys.stderr)
    save_review(doc)
    return 0 if not r["refused"] else 1
  for ln in lines(doc):
    print(ln)
  return 0

if __name__ == "__main__":
  sys.exit(main())
