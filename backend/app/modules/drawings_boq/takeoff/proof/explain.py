from __future__ import annotations
import argparse
import asyncio
import datetime
import json
import os
import re
import sys
import time
from app.modules.drawings_boq.takeoff.proof.bench import failures as FL
from app.engine.catalogue import loader as CL
from app.modules.drawings_boq.takeoff.proof.answers import answers as AN
from app.modules.drawings_boq.takeoff.proof import case_io as CIO
from app.modules.drawings_boq.takeoff.proof.bench import explained as EXD
from app.modules.drawings_boq.takeoff.proof import explain_line as EL
from app.modules.drawings_boq.takeoff.ai_reader import evidence as EV
from app.modules.drawings_boq.takeoff.ai_reader import prompts as PR

PROMPT_NAME = "explain.v1"
FIRST_ID = "E"
SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(\[])")

def settings() -> dict:
  return FL.read_yaml("explain.yaml")

def read_rows(bench_dir: str, run: str) -> list:
  path = os.path.join(bench_dir, "rows.jsonl")
  if not os.path.isfile(path):
    raise FileNotFoundError(f"There is no rows.jsonl in {bench_dir}; run the benchmark first.")
  with open(path, encoding="utf-8") as fh:
    return [r for r in (json.loads(line) for line in fh if line.strip()) if r["run"] == run]

def key_of(row: dict) -> str:
  return f"{row['set']}|{row['element']}|{row['floor']}"

def group_key(row: dict) -> str | None:
  f = FL.failure_of(row)
  return None if f is None else f"{f[0]} / {f[1]} / {row['section']}"

def has_answer(row: dict) -> bool:
  return row["answer_qty"] not in (None, 0)

def gap_pct(row: dict) -> float:
  if row["trace_qty"] is None:
    return 100.0
  return abs(row["diff_pct"]) if row["diff_pct"] is not None else 0.0

def pick(rows: list, top: int) -> list:
  groups = FL.groups(rows)
  by: dict = {}
  for r in rows:
    k = group_key(r)
    if k is not None and has_answer(r):
      by.setdefault(k, []).append(r)
      
  queues = [(g, sorted(by[g["key"]], key=lambda r: (-gap_pct(r), r["set"], r["element"], r["floor"]))) for g in groups if g["key"] in by]
  out, depth = [], 0
  while len(out) < top and any(len(q) > depth for _g, q in queues):
    for g, q in queues:
      if len(q) > depth and len(out) < top:
        out.append((g, q[depth]))
    depth += 1
  return out

def answer_items(doc: dict | None, element: str, floor: str, limit: int) -> list:
  return [it for it in (doc or {}).get("items") or [] if it["element"] == element and (floor == "ALL" or it.get("floor") == floor)][:limit]

def num(v) -> str:
  return f"{float(v):,.2f}"

def facts(row: dict, group: dict, items: list, item, owner: str, breakdown: str | None, s: dict) -> list:
  unit = row["unit"] or ""
  out = []

  def add(text: str) -> None:
    out.append(f"{FIRST_ID}{len(out) + 1} {text}")
  add(f"The catalogue item is {row['element']}, {item.name if item else row['element']}, in the section {row['section']}; the pack that builds its reading is {owner}. The floor is {row['floor']} and the set is {row['set']}.")
  if row["trace_qty"] is None:
    add(f"Trace gives no quantity for it; its state is {row['state']}.")
  else:
    add(f"Trace gives {num(row['trace_qty'])} {unit}; its state is {row['state']}.")
  if row["diff_pct"] is None:
    add(f"The QS file gives {num(row['answer_qty'])} {unit} from {len(items)} line(s) of the workbook.")
  else:
    add(f"The QS file gives {num(row['answer_qty'])} {unit} from {len(items)} line(s) of the workbook; Trace is {row['diff_pct']:+.1f}% from it.")
  reasons = [str(r) for r in row["reasons"]][:s["max_reasons"]]
  add("The reason codes Trace recorded for it are: " + (", ".join(reasons) if reasons else "none") + ".")
  add("Its number came from: " + (", ".join(row["sources"]) if row["sources"] else "nothing, there is no number") + ".")
  pages = [f"{p['pdf']} page {p['page']}" for p in (row.get("pages") or [])[:s["max_pages"]]]
  add("The pages it rests on: " + ("; ".join(pages) if pages else "none found") + ".")
  for n, it in enumerate(items, 1):
    add(f"QS line {n} is \"{it['qs_line']}\" on the sheet \"{it['sheet']}\", rows {it['rows']}, giving {num(it['quantity'])} {it['unit']}; it was matched to this item by {it['mapped_by']}, confirmed by a person: {'yes' if it.get('confirmed') else 'no'}.")
  add(f"The same kind of failure ({group['state']}, {group['reason']}) is in {group['rows']} row(s) of {group['sets']} set(s) of offices {', '.join(group['office_letters'])}.")
  if breakdown:
    add(breakdown)
  return out

def packs_text(owners: dict) -> str:
  sections: dict = {}
  for it in CL.items():
    p = FL.pack_of(it.id, owners)
    if p:
      sections.setdefault(p, [])
      if it.section not in sections[p]:
        sections[p].append(it.section)
  about = owners.get("about") or {}
  return "\n".join(f"- {p}: " + (about.get(p) or ("builds the reading of " + "; ".join(sections.get(p, ["nothing"])))) for p in owners["packs"])

def pack_problems(owners: dict) -> list:
  have, out = set(owners.get("packs") or []), []
  want = {FL.pack_of(it.id, owners) for it in CL.items()} | set((owners.get("by_reason") or {}).values()) | {owners.get("default")}
  for p in sorted(x for x in want if x):
    if p not in have:
      out.append(f"owners.yaml lists no pack {p}, which the catalogue or the reasons name as an owner")
  return out

def breakdowns(sets: list, score_dir: str, cases_dir: str | None) -> dict:
  out: dict = {}
  for name in sets:
    try:
      res = EL.run(name, None, score_dir, cases_dir)
    except Exception as exc:
      print(f"{name}: line breakdown not made: {type(exc).__name__}: {exc}", file=sys.stderr)
      continue
    for e in res["lines"]:
      out[(name, e["line"].split("/")[0])] = f"For the whole line {e['line']} the gap to the QS file splits as: {EL.residual_text(e)}."
  return out

def entries_of(rows: list, s: dict, owners: dict, cross: dict | None = None) -> list:
  answers: dict = {}
  out = []
  for n, (group, row) in enumerate(pick(rows, s["top"]), 1):
    if row["set"] not in answers:
      answers[row["set"]] = AN.load(os.path.join(CIO.HERE, row["set"]))
    items = answer_items(answers[row["set"]], row["element"], row["floor"], s["max_answer_lines"])
    item = CL.get(row["element"])
    line = AN.ledger_line(row["element"], row["unit"])
    more = (cross or {}).get((row["set"], line))
    out.append({"key": key_of(row), "rank": n, "set": row["set"], "office": row["office"], "element": row["element"], "name": item.name if item else row["element"], "floor": row["floor"],
      "section": row["section"], "state": row["state"], "unit": row["unit"], "trace_qty": row["trace_qty"], "answer_qty": row["answer_qty"], "diff_pct": row["diff_pct"],
      "group": group["key"], "suggested_owner": group["suggested_owner"], "pack": facts(row, group, items, item, FL.pack_of(row["element"], owners) or row["owner_pack"], more, s), "draft": None, "right": None, "note": ""})
  return out

def marked(entry: dict) -> bool:
  return bool(entry.get("draft")) or entry.get("right") is not None

def merge(doc: dict, fresh: list) -> dict:
  have = {e["key"]: e for e in doc["entries"]}
  out, added = [], 0
  for e in fresh:
    old = have.pop(e["key"], None)
    if old is not None and marked(old):
      old["rank"] = e["rank"]
      out.append(old)
    else:
      out.append(e)
      added += old is None
      
  left = [e for e in have.values() if marked(e)]
  for n, e in enumerate(left, len(out) + 1):
    e["rank"] = n
  doc["entries"] = out + left
  return {"added": added, "kept_marked": len(left), "dropped": len(have) - len(left)}

def sentences(text: str) -> list:
  return [p for p in SENTENCE_END.split(str(text or "").strip()) if p.strip()]

def checks_of(answer: dict, ids: list, packs: list, pack_text: str, s: dict) -> list:
  cause = str(answer.get("cause") or "").strip()
  cited = answer.get("evidence")
  cited = [str(c) for c in cited] if isinstance(cited, list) else []
  stray = [c for c in cited if c not in ids]
  owner = answer.get("owner")
  
  invented = sorted(EV.printed_numbers(cause) - EV.printed_numbers(pack_text))
  return [EV.result("cause_given", bool(cause), "a cause is given" if cause else "no cause is given"),
    EV.result("cause_short", len(sentences(cause)) <= s["max_sentences"] and len(cause) <= s["max_chars"], f"{len(sentences(cause))} sentence(s), {len(cause)} characters"),
    EV.result("evidence_exists", not stray, "every fact named exists" if not stray else "no such fact: " + ", ".join(stray)),
    EV.result("evidence_named", bool(cited) or owner in (None, ""), "the facts it rests on are named" if cited else "no fact is named and an owner is"),
    EV.choice_offered(owner or None, packs),
    EV.result("numbers_in_facts", not invented, "every number is printed in the facts" if not invented else "not in the facts: " + ", ".join(f"{v:g}" for v in invented[:6]))]

async def draft_one(entry: dict, ask, model: str, packs: list, packs_block: str, s: dict) -> dict:
  pack_text = "\n".join(entry["pack"])
  started = time.monotonic()
  parsed, usage = await ask(PR.render(PROMPT_NAME, pack=pack_text, packs=packs_block))
  answer = parsed if isinstance(parsed, dict) else {}
  failed = [c["name"] for c in checks_of(answer, [p.split(" ", 1)[0] for p in entry["pack"]], packs, pack_text, s) if not c["passed"]]
  owner = answer.get("owner")
  entry["draft"] = {"cause": str(answer.get("cause") or "").strip(), "evidence": [str(c) for c in answer["evidence"]] if isinstance(answer.get("evidence"), list) else [],
    "owner": owner if owner in packs else None, "owner_given": owner, "model": model, "prompt_version": PR.load(PROMPT_NAME)["version"], "checks_failed": failed,
    "input_tokens": (usage or {}).get("input_tokens"), "output_tokens": (usage or {}).get("output_tokens"), "seconds": round(time.monotonic() - started, 2)}
  return entry

def propose(doc: dict, ask, model: str, owners: dict, s: dict, force: bool) -> dict:
  packs = list(owners["packs"])
  block = packs_text(owners)
  todo = [e for e in doc["entries"] if e["right"] is None and (force or not e.get("draft"))]

  async def run():
    for e in todo:
      await draft_one(e, ask, model, packs, block, s)
  asyncio.run(run())
  return {"asked": len(todo), "failed_checks": sum(1 for e in todo if e["draft"]["checks_failed"]), "no_cause": sum(1 for e in todo if not e["draft"]["cause"])}

def lines(doc: dict) -> list:
  out = [EXD.hit_line(doc)]
  for e in doc["entries"]:
    d = e.get("draft")
    mark = "not marked" if e.get("right") is None else ("right" if e["right"] else "wrong")
    out.append(f"{e['rank']:>2}. {e['set']} {e['element']} {e['floor']}: Trace {e['trace_qty']} QS {e['answer_qty']} {e['unit'] or ''} ({e['state']}) -> " + ("no draft yet" if not d else f"{d['owner'] or 'no owner'}: {d['cause'] or '(no cause)'} [{mark}]" + (f" failed: {', '.join(d['checks_failed'])}" if d["checks_failed"] else "")))
  return out

def main(argv: list | None = None) -> int:
  ap = argparse.ArgumentParser(description="Draft the likely cause of the biggest differences between Trace and the QS file, for a person to mark right or wrong. Text only; nothing changes automatically.")
  sub = ap.add_subparsers(dest="cmd", required=True)
  c = sub.add_parser("collect")
  c.add_argument("--bench-dir", required=True, help="the folder a benchmark run wrote (it holds rows.jsonl)")
  c.add_argument("--run", default=None, help="PRODUCT or PROOF; default from explain.yaml")
  c.add_argument("--top", type=int, default=None)
  c.add_argument("--breakdown", action="store_true", help="add the line breakdown of explain_line where a set's folder describes its workbook rows; it runs the score when --score-dir holds none")
  c.add_argument("--score-dir", default="explain_out", help="folder explain_line reads or writes its score in")
  c.add_argument("--cases-dir", default=None)
  p = sub.add_parser("propose")
  p.add_argument("--where", choices=("local", "outside"), required=True, help="local uses Ollama; outside uses the Anthropic API with AI_API_KEY")
  p.add_argument("--model", default=None)
  p.add_argument("--force", action="store_true")
  sub.add_parser("report")
  
  args = ap.parse_args(argv)
  s, owners, doc = settings(), FL.read_yaml("owners.yaml"), EXD.load()
  if args.cmd == "collect":
    bad = pack_problems(owners)
    for b in bad:
      print(b, file=sys.stderr)
    if bad:
      return 1
    s = {**s, "run": args.run or s["run"], "top": args.top or s["top"]}
    rows = read_rows(args.bench_dir, s["run"])
    chosen = pick(rows, s["top"])
    cross = breakdowns(sorted({r["set"] for _g, r in chosen}), args.score_dir, args.cases_dir) if args.breakdown else None
    r = merge(doc, entries_of(rows, s, owners, cross))
    doc["run"], doc["made"] = s["run"], datetime.date.today().isoformat()
    print(f"{len(doc['entries'])} difference(s) from the {s['run']} run: {r['added']} new, {r['kept_marked']} older with a draft or mark kept, {r['dropped']} dropped")
    EXD.save(doc)
  elif args.cmd == "propose":
    from app.modules.ai_requests.service import AIOrchestratorService, CONSENT_PROVIDER, DEFAULT_MAX_TOKENS, model_of
    provider = CONSENT_PROVIDER["LOCAL" if args.where == "local" else "OUTSIDE"]
    model = args.model or model_of(provider)

    async def ask(prompt: str):
      _raw, parsed, usage = await AIOrchestratorService._call_provider(provider, model, prompt, [], DEFAULT_MAX_TOKENS, None)
      return parsed, usage
    r = propose(doc, ask, model, owners, s, args.force)
    print(f"{r['asked']} drafted, {r['failed_checks']} failed a check, {r['no_cause']} with no cause")
    EXD.save(doc)
  for ln in lines(doc):
    print(ln)
  return 0

if __name__ == "__main__":
  sys.exit(main())
