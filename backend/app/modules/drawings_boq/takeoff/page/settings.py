from __future__ import annotations
import functools
import os
import yaml

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.yaml")

class SettingsError(ValueError):
  pass

def _walk(node, path: str, problems: list) -> None:
  if isinstance(node, dict):
    for k, v in node.items():
      _walk(v, f"{path}.{k}" if path else str(k), problems)
  elif isinstance(node, bool) or not isinstance(node, (int, float)):
    problems.append(f"{path}: must be a number")
  elif node <= 0:
    problems.append(f"{path}: must be above zero")

@functools.lru_cache(maxsize=1)
def load() -> dict:
  with open(PATH, encoding="utf-8") as fh:
    doc = yaml.safe_load(fh) or {}
  problems: list = []
  _walk(doc, "", problems)
  if problems:
    raise SettingsError("; ".join(problems))
  return doc

def get(section: str, name: str) -> float:
  return float(load()[section][name])

def top(name: str) -> float:
  return float(load()[name])
