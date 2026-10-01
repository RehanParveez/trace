from __future__ import annotations
from typing import Iterable
from collections import Counter
from decimal import ROUND_HALF_UP, Decimal

MAX_ELEMENT_IDS_PER_ISSUE = 50
_SEVERITY_RANK = {"error": 0, "warning": 1, "info": 2}


def summarize_audit(elements: Iterable, model_issues: list[dict] | None = None) -> dict:
  rows = list(elements)
  total = len(rows)

  status_counts: Counter = Counter()
  role_counts: Counter = Counter()
  geometry_counts: Counter = Counter()
  buckets: dict[str, dict] = {}

  for row in rows:
    status_counts[row.normalization_status or "PENDING"] += 1
    role_counts[row.structural_role or "UNKNOWN"] += 1
    geometry_counts[row.geometry_kind or "NONE"] += 1
    for issue in row.normalization_issues or []:
      code = issue.get("code", "UNKNOWN")
      bucket = buckets.get(code)
      if bucket is None:
        bucket = {
          "code": code,
          "severity": issue.get("severity", "info"),
          "message": issue.get("message", ""),
          "count": 0,
          "element_ids": [],
        }
        buckets[code] = bucket
      bucket["count"] += 1
      if len(bucket["element_ids"]) < MAX_ELEMENT_IDS_PER_ISSUE:
        bucket["element_ids"].append(str(row.id))

  for issue in model_issues or []:
    code = issue.get("code", "UNKNOWN")
    buckets.setdefault(
      f"MODEL:{code}",
      {
        "code": code,
        "severity": issue.get("severity", "info"),
        "message": issue.get("message", ""),
        "count": 1,
        "element_ids": [],
        "scope": "model",
      },
    )

  issues = sorted(
    buckets.values(),
    key=lambda b: (_SEVERITY_RANK.get(b["severity"], 3), -b["count"], b["code"]),
  )

  valid = status_counts.get("VALID", 0)
  score = (
    (Decimal(valid) * 100 / Decimal(total)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if total
    else Decimal("0.00")
  )

  def _count(code: str) -> int:
    bucket = buckets.get(code)
    return bucket["count"] if bucket else 0

  return {
    "overall_score": score,
    "element_count": total,
    "issues": issues,
    "missing_material_count": _count("MISSING_MATERIAL"),
    "zero_quantity_count": _count("NO_QUANTITY"),
    "unclassified_proxy_count": _count("UNCLASSIFIED_ELEMENT"),
    "extra_stats": {
      "by_status": dict(status_counts),
      "by_role": dict(role_counts),
      "by_geometry_kind": dict(geometry_counts),
      "blocking_error_count": sum(b["count"] for b in issues if b["severity"] == "error"),
      "model_issues": list(model_issues or []),
    },
  }