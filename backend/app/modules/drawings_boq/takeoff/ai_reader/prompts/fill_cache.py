from __future__ import annotations
import argparse
import asyncio
import os
import sys
import time
from app.modules.ai_requests.models import AIProvider
from app.modules.ai_requests.service import AIOrchestratorService, AIRunResult, CONSENT_PROVIDER, DEFAULT_MAX_TOKENS, model_of
from app.modules.drawings_boq.takeoff.ai_reader import cache as CACHE
from app.modules.drawings_boq.takeoff.ai_reader import candidate as CAND
from app.modules.drawings_boq.takeoff.ai_reader import contract as C
from app.modules.drawings_boq.takeoff.ai_reader import reader as RD
from app.modules.drawings_boq.takeoff.ai_reader import regions as RG
from app.modules.drawings_boq.takeoff.ai_reader import tasks as TASKS
from app.modules.drawings_boq.takeoff.prep.extract import open_document

def pages_of(spec: str | None, total: int) -> list:
  if not spec:
    return list(range(1, total + 1))
  out: list = []
  for part in spec.split(","):
    a, _, b = part.strip().partition("-")
    out.extend(range(int(a), int(b or a) + 1))
  return [p for p in dict.fromkeys(out) if 1 <= p <= total]

def entry_of(*, record: dict, sha: str, page: int, provider: AIProvider) -> dict:
  boxes = record["crop"].get("boxes") or []
  union = [min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes)] if boxes else None
  value = record["ai_value"]
  quotes = [value.get(k) for k in C.TEXT_KEYS] if value else []
  candidate = CAND.build(task=record["task"], page=page, value=value or {}, quotes=quotes, bbox=union, confidence=(value or {}).get("confidence"), model=record["model"],
    prompt=record["prompt"], prompt_version=record["prompt_version"], cache_key=record["cache_key"], validators=record["validators"], shadow=True,
    input_tokens=record["input_tokens"], output_tokens=record["output_tokens"])
  return {"cache_key": record["cache_key"], "task": record["task"], "pdf_sha256": sha, "page": page, "region": RG.title_block_region(), "prompt_version": record["prompt_version"],
    "model": record["model"], "provider": provider.value, "seconds": record["seconds"], "input_tokens": record["input_tokens"], "output_tokens": record["output_tokens"],
    "status": record["status"], "problems": record["problems"], "error": record["error"], "answer": value, "validators": record["validators"], "candidate": candidate}

async def fill(*, pdf: str, out: str, provider: AIProvider, model: str, pages: str | None, force: bool, max_tokens: int, timeout_s: float | None) -> dict:
  with open(pdf, "rb") as fh:
    contents = fh.read()
  sha = CACHE.pdf_sha256(contents)
  doc = open_document(contents)
  total = len(doc)
  doc.close()
  region = RG.title_block_region()
  stats = {"pages": 0, "asked": 0, "cached": 0, "failed": 0, "seconds": 0.0, "input_tokens": 0, "output_tokens": 0}

  async def ask(prompt: str, png: bytes):
    started = time.monotonic()
    try:
      raw, parsed, usage = await AIOrchestratorService._call_provider(provider, model, prompt, [(png, "image/png")], max_tokens, timeout_s)
      return AIRunResult(success=True, parsed_output=parsed, raw_response=raw, input_tokens=usage.get("input_tokens"), output_tokens=usage.get("output_tokens"),
        model=model, provider=provider.value, seconds=time.monotonic() - started)
    except Exception as exc:
      return AIRunResult(success=False, error_message=str(exc), model=model, provider=provider.value, seconds=time.monotonic() - started)

  for page in pages_of(pages, total):
    stats["pages"] += 1
    key = CACHE.key(sha, page, region, RD.TASK, C.PROMPT_VERSION, model)
    if not force and CACHE.read(out, key) is not None:
      stats["cached"] += 1
      continue
    record = await RD.read_sheet(contents=contents, page_no=page, ask=ask, cache_key=key, model=model)
    stats["asked"] += 1
    stats["seconds"] += record["seconds"] or 0.0
    stats["input_tokens"] += record["input_tokens"] or 0
    stats["output_tokens"] += record["output_tokens"] or 0
    if record["status"] == RD.FAILED:
      stats["failed"] += 1
      print(f"page {page}: failed: {record['error']}", file=sys.stderr)
      continue
    CACHE.write(out, entry_of(record=record, sha=sha, page=page, provider=provider))
  stats["seconds"] = round(stats["seconds"], 2)
  return stats

def main(argv: list | None = None) -> int:
  ap = argparse.ArgumentParser(description="Ask a model for the SHEET task on the pages of one PDF and write each answer to a case's ai_cache folder. The proof reads those files and never asks a model.")
  ap.add_argument("--pdf", required=True)
  ap.add_argument("--out", required=True, help="the case folder; answers go to <out>/ai_cache/<key>.json")
  ap.add_argument("--task", default=RD.TASK)
  ap.add_argument("--where", choices=("local", "outside"), required=True, help="local uses Ollama; outside uses the Anthropic API with AI_API_KEY")
  ap.add_argument("--model", default=None)
  ap.add_argument("--pages", default=None, help="for example 1-5,9; all pages when omitted")
  ap.add_argument("--force", action="store_true")
  ap.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
  ap.add_argument("--timeout", type=float, default=None)
  args = ap.parse_args(argv)
  if args.task != RD.TASK or not TASKS.get(args.task).prompt:
    print(f"The task {args.task} has no prompt yet; only {RD.TASK} can be read.", file=sys.stderr)
    return 2
  provider = CONSENT_PROVIDER["LOCAL" if args.where == "local" else "OUTSIDE"]
  model = args.model or model_of(provider)
  stats = asyncio.run(fill(pdf=args.pdf, out=args.out, provider=provider, model=model, pages=args.pages, force=args.force, max_tokens=args.max_tokens, timeout_s=args.timeout))
  print(f"{provider.value} {model}: {stats['pages']} page(s), {stats['asked']} asked, {stats['cached']} already cached, {stats['failed']} failed, {stats['seconds']} s, {stats['input_tokens']} input and {stats['output_tokens']} output tokens")
  return 0 if not stats["failed"] else 1

if __name__ == "__main__":
  sys.exit(main())
