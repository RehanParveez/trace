from __future__ import annotations

OVERLAP_KEY = "scope_overlaps"
MIN_SHARED = 3
MIN_RATIO = 0.05

def find_scope_overlaps(shared: dict, counts: dict, names: dict) -> list[dict]:
  found: list[dict] = []
  
  for (a, b), n in shared.items():
    smaller = min(counts.get(a, 0), counts.get(b, 0))
    if n <= 0 or smaller <= 0:
      continue
    ratio = n / smaller
    if n < MIN_SHARED or ratio < MIN_RATIO:
      continue
    first, second = sorted((a, b), key=lambda i: (names.get(i, "").lower(), i))
    found.append({
      "drawing_a_id": first, "drawing_a_name": names.get(first, ""),
      "drawing_b_id": second, "drawing_b_name": names.get(second, ""),
      "shared_elements": int(n), "share": round(min(ratio, 1.0), 4),
    })
  return sorted(found, key=lambda o: (-o["share"], o["drawing_a_name"].lower(), o["drawing_b_name"].lower()))

def overlap_message(overlaps: list[dict]) -> str:
  lines = [
    f"{o['drawing_a_name']} and {o['drawing_b_name']} share {o['shared_elements']} elements "
    f"({round(o['share'] * 100)}% of the smaller file)"
    for o in overlaps[:4]
  ]
  more = f" and {len(overlaps) - 4} more pair(s)" if len(overlaps) > 4 else ""
  return ("The selected drawings describe some of the same elements, so measuring them together would count those "
    "elements twice: " + "; ".join(lines) + more + ".")