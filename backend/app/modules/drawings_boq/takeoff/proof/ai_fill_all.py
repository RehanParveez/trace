from __future__ import annotations
import argparse
import asyncio
import json
import os
import sys
from app.modules.ai_requests import cap as CAP
from app.modules.drawings_boq.takeoff.ai_reader import cost as COST
from app.modules.drawings_boq.takeoff.ai_reader import legend as LG
from app.modules.drawings_boq.takeoff.ai_reader import notes as NT
from app.modules.drawings_boq.takeoff.ai_reader import reader as RD
from app.modules.drawings_boq.takeoff.ai_reader import schedule as SCH
from app.modules.drawings_boq.takeoff.prep.extract import open_document
from app.modules.drawings_boq.takeoff.proof import case_io as CIO

TASKS = (RD.TASK, NT.TASK, SCH.TASK, LG.TASK)
CAPPED = 3

def plan(cases_dir: str, root: str, audit: bool, only: list) -> tuple:
  items, problems = [], []
  for name in CIO.list_cases(root, audit=audit):
    if only and name not in only:
      continue
    folder = os.path.join(root, name)
    found, bad = CIO.find_files(CIO.load_case(folder), cases_dir)
    problems += [f"{name}: {p}" for p in bad]
    items += [{"case": name, "folder": folder, "pdf": pdf, "path": path} for pdf, path in sorted(found.items())]
  return items, problems

def pages_for(task: str, contents: bytes, total: int) -> tuple:
  if task != LG.TASK:
    return None, total
  pages = [p for p in range(1, total + 1) if LG.page_rows(contents, p)]
  return ",".join(str(p) for p in pages), len(pages)

def cost_of(stats: dict, model: str) -> dict:
  row = {"model": model, "input_tokens": stats["input_tokens"], "output_tokens": stats["output_tokens"], "seconds": stats["seconds"]}
  return COST.summarise([row])

def estimate(rows: list, model: str, root: str) -> dict:
  from app.modules.ai_requests.service import DEFAULT_MAX_TOKENS
  per_call = CAP.next_call_usd(model, DEFAULT_MAX_TOKENS)
  pages = sum(r["pages"] for r in rows)
  by_task = {t: sum(r["pages"] for r in rows if r["task"] == t) for t in sorted({r["task"] for r in rows})}
  spent = COST.cache_spent_usd(root)
  return {"model": model, "pages": pages, "by_task": by_task, "per_call_usd": per_call, "at_most_usd": None if per_call is None else round(per_call * pages, 4), "spent_usd": round(spent, 4), "cap_usd": CAP.settings.ai_monthly_cap_usd}

def estimate_text(e: dict) -> str:
  tasks = ", ".join(f"{t} {n}" for t, n in e["by_task"].items())
  if e["per_call_usd"] is None:
    return f"{e['pages']} page call(s) ({tasks}); {e['model']} has no price in AI_PRICE_USD_PER_MILLION, so no cost is bounded and a paid run would be refused."
  return (f"{e['pages']} page call(s) ({tasks}); at most {e['at_most_usd']} USD if none is cached already ({e['per_call_usd']:.5f} USD a call at {e['model']}'s price); "
    f"{e['spent_usd']} USD already kept this month against a cap of {e['cap_usd']:.2f} USD.")

def render(rows: list, dry: bool, note: str = "") -> str:
  head = "| Case | PDF | Task | Pages |" + ("" if dry else " Asked | Already cached | Failed | Seconds | Input tokens | Output tokens | Rupees |")
  sep = "|---|---|---|---|" + ("" if dry else "---|---|---|---|---|---|---|")
  out = [head, sep]
  for r in rows:
    tail = "" if dry else f" {r['asked']} | {r['cached']} | {r['failed']} | {r['seconds']} | {r['input_tokens']} | {r['output_tokens']} | {r['pkr']} |"
    out.append(f"| {r['case']} | {r['pdf']} | {r['task']} | {r['pages']} |{tail}")
  if not dry:
    t = {k: sum(r[k] for r in rows) for k in ("pages", "asked", "cached", "failed", "seconds", "input_tokens", "output_tokens", "pkr")}
    out.append(f"| **all** | | | {t['pages']} | {t['asked']} | {t['cached']} | {t['failed']} | {round(t['seconds'], 1)} | {t['input_tokens']} | {t['output_tokens']} | {round(t['pkr'], 2)} |")
  return "\n".join(out) + "\n" + (f"\n{note}\n" if note else "")

def main(argv: list | None = None) -> int:
  ap = argparse.ArgumentParser(description="Ask the model for every AI task on every PDF of every case folder and write the answers to each case's ai_cache. The proof reads those files and never asks a model. A PDF that is not in the cases folder stops the run: no set is left out.")
  ap.add_argument("--where", choices=("local", "outside"), help="local uses Ollama; outside uses the Anthropic API with AI_API_KEY (not needed with --dry-run)")
  ap.add_argument("--cases-dir", help="the folder with the case PDFs (default: TRACE_CASES_DIR)")
  ap.add_argument("--root", default=CIO.HERE, help="the folder of case folders")
  ap.add_argument("--tasks", default=",".join(TASKS), help="comma-separated; default: " + ", ".join(TASKS))
  ap.add_argument("--case", action="append", default=[], help="only this case folder (repeat for more)")
  ap.add_argument("--audit", action="store_true", help="also the bar schedule audit cases (a 100-page schedule: it costs more)")
  ap.add_argument("--model", default=None)
  ap.add_argument("--force", action="store_true")
  ap.add_argument("--dry-run", action="store_true", help="count the pages to be asked and ask nothing")
  ap.add_argument("--timeout", type=float, default=None)
  ap.add_argument("--out", default="ai_fill_out", help="a folder for ai_fill.json and ai_fill.md")
  
  args = ap.parse_args(argv)
  tasks = [t.strip() for t in args.tasks.split(",") if t.strip()]
  unknown = [t for t in tasks if t not in TASKS]
  
  if unknown:
    print(f"No such task: {', '.join(unknown)}. The tasks are {', '.join(TASKS)}.", file=sys.stderr)
    return 2
  if not args.dry_run and not args.where:
    print("Name the route: --where local (Ollama) or --where outside (the Anthropic API).", file=sys.stderr)
    return 2
  cases_dir = CIO.cases_dir(args.cases_dir)
  if not cases_dir:
    print(f"Name the folder with the PDFs: --cases-dir, or set {CIO.CASES_DIR_ENV}.", file=sys.stderr)
    return 2
  items, problems = plan(cases_dir, args.root, args.audit, args.case)
  if problems:
    print("\n".join(problems), file=sys.stderr)
    return 2
  
  provider = model = None
  if not args.dry_run:
    from app.modules.ai_requests.service import CONSENT_PROVIDER, DEFAULT_MAX_TOKENS, model_of
    from app.modules.drawings_boq.takeoff.ai_reader import fill_cache as FC
    provider = CONSENT_PROVIDER["LOCAL" if args.where == "local" else "OUTSIDE"]
    model = args.model or model_of(provider)
  rows, failed, stopped = [], 0, None
  
  for item in items:
    with open(item["path"], "rb") as fh:
      contents = fh.read()
    doc = open_document(contents)
    total = len(doc)
    doc.close()
    for task in tasks:
      spec, count = pages_for(task, contents, total)
      row = {"case": item["case"], "pdf": item["pdf"], "task": task, "pages": count, "asked": 0, "cached": 0, "failed": 0, "seconds": 0.0, "input_tokens": 0, "output_tokens": 0, "pkr": 0.0}
      if count and not args.dry_run:
        stats = asyncio.run(FC.fill(pdf=item["path"], out=item["folder"], provider=provider, model=model, pages=spec, force=args.force, max_tokens=DEFAULT_MAX_TOKENS, timeout_s=args.timeout, task=task, mode=LG.WEAK, spend_root=args.root))
        row.update({k: stats[k] for k in ("asked", "cached", "failed", "seconds", "input_tokens", "output_tokens")})
        row["pkr"] = cost_of(stats, model)["pkr"]
        failed += stats["failed"]
        stopped = stats.get("capped")
      rows.append(row)
      print(f"{item['case']} {item['pdf']} {task}: {count} page(s)" + ("" if args.dry_run else f", {row['asked']} asked, {row['cached']} cached, {row['failed']} failed"))
      if stopped:
        break
    if stopped:
      break
      
  bound = None
  if args.dry_run or stopped:
    from app.modules.ai_requests.service import CONSENT_PROVIDER, model_of
    bound = estimate(rows, model or args.model or model_of(CONSENT_PROVIDER["OUTSIDE"]), args.root)
  note = (estimate_text(bound) if args.dry_run else "") + (f"Stopped before the run was finished: {stopped}" if stopped else "")
  os.makedirs(args.out, exist_ok=True)
  with open(os.path.join(args.out, "ai_fill.json"), "w", encoding="utf-8", newline="\n") as fh:
    json.dump({"model": model, "where": args.where, "dry_run": args.dry_run, "rows": rows, "estimate": bound if args.dry_run else None, "stopped": stopped}, fh, indent=1, sort_keys=True)
  with open(os.path.join(args.out, "ai_fill.md"), "w", encoding="utf-8", newline="\n") as fh:
    fh.write(render(rows, args.dry_run, note))
  if args.dry_run:
    print(estimate_text(bound))
    
  print(f"{len(items)} PDF(s) in {len({i['case'] for i in items})} case folder(s); written to {args.out}")
  if stopped:
    print(f"stopped: {stopped}", file=sys.stderr)
    return CAPPED
  return 1 if failed else 0

if __name__ == "__main__":
  sys.exit(main())
