from __future__ import annotations
import logging
import sys
import json
import time
from contextlib import contextmanager

try:
  import resource  
except ImportError: 
  resource = None

logger = logging.getLogger("trace.calc")

def rss_mb() -> int:
  if resource is not None:
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(peak / (1024 * 1024) if sys.platform == "darwin" else peak / 1024)
  try:
    import psutil
    return int(psutil.Process().memory_info().rss / (1024 * 1024))
  except Exception:
    return 0

def current_rss_mb() -> int | None:
  try:
    with open("/proc/self/statm") as fh:
      pages = int(fh.read().split()[1])
    return int(pages * resource.getpagesize() / (1024 * 1024))
  except Exception:
    return None

def log_event(event: str, *, run_id=None, organization_id=None, engine_version: str | None = None, level: int = logging.INFO,
  **fields) -> None:
  record = {"event": event, "run_id": str(run_id) if run_id else None,
    "organization_id": str(organization_id) if organization_id else None, "engine_version": engine_version, **fields}
  logger.log(level, json.dumps(record, default=str, sort_keys=False))

@contextmanager
def timed():
  class _T:
    ms = 0
  t = _T()
  start = time.perf_counter()
  try:
    yield t
  finally:
    t.ms = int((time.perf_counter() - start) * 1000)

FAILURE_CODES = {
  "INPUT_CHANGED": "drawings or rules changed between request and execution",
  "RULE_SET_NOT_FOUND": "the rule set was deleted before the run started",
  "SELF_CHECK_FAILED": "an engine invariant failed (see run_stage_log)",
  "RUN_FAILED": "unexpected error in a stage",
  "RUN_STALE": "the worker stopped reporting progress and the retry budget was spent",
  "RUN_ENQUEUE_FAILED": "the task could not be queued",
  "RUN_ENQUEUE_LOST": "the queued task was never picked up and the retry budget was spent",
  "RUN_TIME_LIMIT": "the soft time limit was reached",
  "RUN_ATTEMPT_SUPERSEDED": "another attempt took over this run",
}