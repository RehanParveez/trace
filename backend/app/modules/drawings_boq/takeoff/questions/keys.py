from __future__ import annotations

INPUT, CONFIRM, CONFLICT, METHOD, SUPPLY = "INPUT", "CONFIRM", "CONFLICT", "METHOD", "SUPPLY"
KINDS = (INPUT, CONFIRM, CONFLICT, METHOD, SUPPLY)
ACCEPT, REJECT = "ACCEPT", "REJECT"
PRINTED, DRAWN = "PRINTED", "DRAWN"
NOT_IN_SCOPE = "NOT_IN_SCOPE"
HEIGHT_INPUT = "height"
FIRST = {"storeys": INPUT, "inputs": INPUT, "reading": CONFIRM, "conflict": CONFLICT, "method": METHOD, "sets": SUPPLY, "sheets": SUPPLY}

def input_key(about: str, floor: str | None = None) -> str:
  return "storeys.ALL.ftf_mm" if about == HEIGHT_INPUT else f"inputs.{about}"

def answer_keys(about: str, floor: str | None) -> list:
  own = [f"storeys.{floor}.ftf_mm"] if about == HEIGHT_INPUT and floor and floor != "ALL" else []
  return own + [input_key(about)]

def reading_key(cls: str) -> str:
  return f"reading.{cls}"

def conflict_key(cls: str, mark: str | None) -> str:
  return f"conflict.{cls}.{mark or 'UNMARKED'}"

def method_key(mid: str) -> str:
  return f"method.{mid}"

def sets_key(name: str) -> str:
  return f"sets.{name}"

def sheets_key(kind: str) -> str:
  return "sheets." + kind.replace("/", ".")

def kind_of(key: str) -> str | None:
  return FIRST.get(str(key).split(".", 1)[0]) if "." in str(key) else None

def is_question_key(key: str) -> bool:
  return kind_of(key) is not None

def method_id(key: str) -> str:
  return key.split(".", 1)[1]

def set_name(key: str) -> str:
  return key.split(".", 1)[1]
