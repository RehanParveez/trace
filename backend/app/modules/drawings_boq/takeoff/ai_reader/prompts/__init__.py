from __future__ import annotations
import functools
import pathlib
import yaml

HERE = pathlib.Path(__file__).resolve().parent
KEYS = ("task", "version", "schema", "text")

class PromptError(Exception):
  pass

@functools.lru_cache(maxsize=None)
def load(name: str) -> dict:
  path = HERE / f"{name}.yaml"
  if not path.is_file():
    raise PromptError(f"There is no prompt file {name}.yaml.")
  with open(path, encoding="utf-8") as fh:
    data = yaml.safe_load(fh)
  if not isinstance(data, dict) or any(not data.get(k) for k in KEYS):
    raise PromptError(f"{name}.yaml must give {', '.join(KEYS)}.")
  return {**data, "version": str(data["version"])}

def render(name: str, **slots: str) -> str:
  text = load(name)["text"]
  for key, value in slots.items():
    text = text.replace("{" + key + "}", value)
  return text

def names() -> list:
  return sorted(p.stem for p in HERE.glob("*.yaml"))
