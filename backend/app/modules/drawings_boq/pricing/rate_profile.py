from __future__ import annotations
from dataclasses import dataclass
from functools import lru_cache
import pathlib
import yaml

PROFILES_FILE = pathlib.Path(__file__).with_name("rate_book_profiles.yaml")

@dataclass(frozen=True)
class RateBookProfile:
  id: str
  province: str | None
  city: str | None
  full_price_chapters: frozenset
  confirmed_by: str

  def full_price(self, chapter_no) -> bool:
    return chapter_no is not None and chapter_no in self.full_price_chapters

def _norm(text) -> str:
  return (text or "").strip().lower()

@lru_cache(maxsize=1)
def load() -> tuple:
  with open(PROFILES_FILE, encoding="utf-8") as fh:
    data = yaml.safe_load(fh) or {}
  out = []
  for p in data.get("profiles") or []:
    out.append(RateBookProfile(str(p["id"]), p.get("province"), p.get("city"), frozenset(int(c) for c in p.get("full_price_chapters") or []), str(p.get("confirmed_by") or "")))
  return tuple(out)

def for_place(province, city) -> RateBookProfile | None:
  province, city = _norm(province), _norm(city)
  if not province:
    return None
  mine = [p for p in load() if _norm(p.province) == province]
  return next((p for p in mine if city and _norm(p.city) == city), None) or next((p for p in mine if not p.city), None)
