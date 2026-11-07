from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
import re
import yaml

KINDS = ("CONCRETE", "MORTAR")
MATERIALS = ("cement_bags", "sand_cft", "aggregate_cft")

@dataclass(frozen=True)
class Row:
  kind: str
  mix: str
  per_qty: Decimal           
  unit: str                  
  cement_bags: Decimal | None
  sand_cft: Decimal | None
  aggregate_cft: Decimal | None
  page: int | None = None

@dataclass(frozen=True)
class Table:
  edition: str
  rows: tuple
  source: str = ""

def mix_key(text: str | None) -> str:
  """'1 : 2 : 4', '1:2:4' and '1-2-4' are the same mix."""
  return re.sub(r"\s*[:\-/]\s*", ":", (text or "").strip())

def parse(data: dict) -> Table:
  rows = []
  for r in data.get("rows") or []:
    kind = str(r["kind"]).upper()
    if kind not in KINDS:
      raise ValueError(f"coefficient kind '{kind}' is not one of {KINDS}")
    per = Decimal(str(r["per_qty"]))
    if per <= 0:
      raise ValueError("a coefficient row is printed for a positive quantity")
    rows.append(Row(kind, mix_key(str(r["mix"])), per, str(r.get("unit", "cft")), *(None if r.get(m) is None else Decimal(str(r[m])) for m in MATERIALS), r.get("page")))
  return Table(str(data["edition"]), tuple(rows), str(data.get("source") or ""))

def load(path: str) -> Table:
  with open(path, encoding="utf-8") as fh:
    return parse(yaml.safe_load(fh) or {})

def find(table: Table | None, kind: str, mix: str | None) -> Row | None:
  if table is None or not mix:
    return None
  key = mix_key(mix)
  return next((r for r in table.rows if r.kind == kind and r.mix == key), None)
