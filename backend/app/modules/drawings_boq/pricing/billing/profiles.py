from __future__ import annotations
from dataclasses import dataclass
from functools import lru_cache
import pathlib
import yaml

FILE = pathlib.Path(__file__).with_name("profiles.yaml")
DEFAULT_PROFILE = "PRIVATE_QS"

@dataclass(frozen=True)
class Profile:
  id: str
  label: str
  block: str
  split_by_floor: bool
  split_by_floor_codes: frozenset
  included_in: dict

@lru_cache(maxsize=1)
def _raw() -> dict:
  with open(FILE, encoding="utf-8") as fh:
    return yaml.safe_load(fh) or {}

def all_profiles() -> dict:
  return {p["id"]: Profile(p["id"], p.get("label", p["id"]), p["block"], bool(p.get("split_by_floor")), frozenset(p.get("split_by_floor_codes") or ()), dict(p.get("included_in") or {}))
    for p in _raw().get("profiles") or []}

def get(profile_id: str) -> Profile:
  found = all_profiles().get(profile_id)
  if found is None:
    raise ValueError(f"unknown billing profile '{profile_id}'")
  return found

def choose(project: str | None, company_default: str | None) -> Profile:
  for wanted in (project, company_default):
    if wanted and wanted in all_profiles():
      return get(wanted)
  return get(DEFAULT_PROFILE)

def spec_defaults() -> dict:
  return dict(_raw().get("spec_defaults") or {})

def spec_question(name: str) -> str:
  return (_raw().get("spec_questions") or {}).get(name) or f"What is the {name.replace('_', ' ')} of this work?"
