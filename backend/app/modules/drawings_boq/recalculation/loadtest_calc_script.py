from __future__ import annotations
import sys
from pathlib import Path
import asyncio
import time
import statistics
import json
import argparse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

CALC_BUDGET_S = 300
API_P95_BUDGET_MS = 500

def _grid(text: str) -> tuple:
  nx, ny, nz = (int(v) for v in text.lower().split("x"))
  return nx, ny, nz

def _p95(values: list) -> float:
  ordered = sorted(values)
  return ordered[min(int(len(ordered) * 0.95), len(ordered) - 1)] if ordered else 0.0

async def main(args) -> int:
  from app.core.database import WorkerSessionLocal, dispose_worker_engine
  from app.dependencies.tenancy import scope_session_as_platform_admin
  from backend.app.modules.drawings_boq.recalculation import loadtest
  from app.modules.drawings_boq.calc_service import CalculationService
  from app.modules.drawings_boq.schemas import LedgerRowResponse
  from pydantic import TypeAdapter

  report: dict = {"grid": args.grid, "budgets": {}}
  async with WorkerSessionLocal() as session:
    await scope_session_as_platform_admin(session)
    org = await loadtest.ensure_organization(session, plan_slug=args.plan)
    org_id = org.id
    t = time.perf_counter()
    synthetic = await loadtest.seed_synthetic_project(session, org_id, grid=_grid(args.grid))
    report["elements"] = synthetic.elements
    report["seed_s"] = round(time.perf_counter() - t, 2)
    print(f"seeded {synthetic.elements} elements in {report['seed_s']} s", flush=True)

    first = await loadtest.run_to_completion(session, org_id, synthetic.project_id)
    if first.get("status") != "COMPLETED":
      print("FIRST RUN FAILED:", first.get("error"))
      return 2
    report["full_run"] = {"execute_s": round(first["execute_s"], 2), "request_s": round(first["request_s"], 2),
      "mode": first["mode"], "timings_ms": first["metrics"].get("timings_ms"),
      "peak_rss_mb": first["metrics"].get("peak_rss_mb"), "counts": first["metrics"].get("counts")}
    print(f"full run: {first['execute_s']:.1f} s  (request {first['request_s']:.1f} s)", flush=True)

    again = await loadtest.run_to_completion(session, org_id, synthetic.project_id)
    report["unchanged_rerun"] = {"reused_existing_run": again["reused"], "request_s": round(again["request_s"], 2)}

    if args.edits:
      await loadtest.edit_columns(session, synthetic, org_id, args.edits)
      incr = await loadtest.run_to_completion(session, org_id, synthetic.project_id, verify=True)
      if incr.get("status") != "COMPLETED":
        print("INCREMENTAL RUN FAILED:", incr.get("error"))
        
        return 2
      verify = (incr["metrics"] or {}).get("verify") or {}
      report["incremental_run"] = {"execute_s": round(incr["execute_s"], 2), "mode": incr["mode"],
        "allocation": incr["metrics"].get("allocation"), "verify": verify, "timings_ms": incr["metrics"].get("timings_ms")}
      print(f"incremental run ({args.edits} edits): {incr['execute_s']:.1f} s mode={incr['mode']} verify={verify}", flush=True)
      report["budgets"]["incremental_matches_full"] = bool(verify.get("matched"))

      await loadtest.edit_columns(session, synthetic, org_id, args.edits, dx=-90.0)
      plain = await loadtest.run_to_completion(session, org_id, synthetic.project_id)
      if plain.get("status") != "COMPLETED":
        print("UNVERIFIED INCREMENTAL RUN FAILED:", plain.get("error"))
        return 2
    
      report["incremental_run_unverified"] = {"execute_s": round(plain["execute_s"], 2), "mode": plain["mode"],
        "allocation": plain["metrics"].get("allocation"), "timings_ms": plain["metrics"].get("timings_ms"),
        "peak_rss_mb": plain["metrics"].get("peak_rss_mb")}
      print(f"incremental run, no verify: {plain['execute_s']:.1f} s mode={plain['mode']}", flush=True)
      report["budgets"]["incremental_run_stays_incremental"] = plain["mode"] == "INCREMENTAL"
      incr = plain

    run_id = (incr if args.edits else first)["run_id"]
    service = CalculationService(session)
    adapter = TypeAdapter(list[LedgerRowResponse])
    samples = []
    after = None
    
    for _ in range(args.pages):
      t = time.perf_counter()
      rows, after = await service.list_ledger(org_id, run_id, limit=500, after=after)
      adapter.dump_python(adapter.validate_python(rows, from_attributes=True), mode="json")
      samples.append((time.perf_counter() - t) * 1000)
      if after is None:
        after = None
    report["api_reads"] = {"pages": len(samples), "p50_ms": round(statistics.median(samples), 1),
      "p95_ms": round(_p95(samples), 1), "max_ms": round(max(samples), 1)}
    print(f"ledger pages: p50 {report['api_reads']['p50_ms']} ms  p95 {report['api_reads']['p95_ms']} ms", flush=True)

    report["budgets"]["calc_under_5_min"] = first["execute_s"] < CALC_BUDGET_S
    report["budgets"]["api_p95_under_500_ms"] = _p95(samples) < API_P95_BUDGET_MS
    report["budgets"]["memory_within_budget"] = bool(first["metrics"].get("within_memory_budget", True))
    report["budgets"]["unchanged_rerun_is_free"] = bool(again["reused"])
  await dispose_worker_engine()

  print(json.dumps(report["budgets"], indent=2))
  if args.json:
    Path(args.json).write_text(json.dumps(report, indent=2, default=str))
  return 0 if all(report["budgets"].values()) else 1

if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  parser.add_argument("--grid", default="20x20x12", help="columns x columns x storeys; 20x20x12 is about 18.7k elements")
  parser.add_argument("--edits", type=int, default=25, help="columns to move before the incremental run (0 = skip)")
  parser.add_argument("--pages", type=int, default=40, help="ledger pages to time")
  parser.add_argument("--plan", default="professional")
  parser.add_argument("--json", default=None, help="write the full report here")
  sys.exit(asyncio.run(main(parser.parse_args())))