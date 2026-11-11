from __future__ import annotations
import functools
import os
import re
import yaml

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "choices_pk.yaml")
PRINTED, DECIDED, DEFAULT, OPEN = "PRINTED", "DECIDED", "DEFAULT", "OPEN"
STATES = (PRINTED, DECIDED, DEFAULT, OPEN)
PREFIX = "choice."
VARIANT = "VARIANT-"
USE_DEFAULTS = "USE_QS_DEFAULTS"
YES = "yes"
CARD_FIELDS = ("id", "label", "asks", "applies_to", "read", "spec", "options", "default")
OPTION_FIELDS = ("text", "spec_values", "record", "mrs_item", "mrs_ref")
CODE = re.compile(r"^\d{1,2}-\d{1,3}(?:\([a-z]\))?(?:to\d{1,2}-\d{1,3})?$")

class ChoiceError(Exception):
  pass

@functools.lru_cache(maxsize=1)
def _raw() -> dict:
  with open(PATH, encoding="utf-8") as fh:
    data = yaml.safe_load(fh)
  if not isinstance(data, dict) or not isinstance(data.get("cards"), list):
    raise ChoiceError("choices_pk.yaml must hold a list of cards")
  return data

def key_of(card_id: str) -> str:
  return PREFIX + card_id

def id_of(key: str) -> str:
  return str(key)[len(PREFIX):]

def is_key(key: str) -> bool:
  return str(key).startswith(PREFIX)

def variant_cards() -> list:
  from app.engine.catalogue import loader
  out = []
  for it in sorted(loader.items(), key=lambda i: i.id):
    by: dict = {}
    for b in it.billing.MRS_PB:
      by.setdefault(b.qty, [])
      if b.item not in by[b.qty]:
        by[b.qty].append(b.item)
    for qty, codes in by.items():
      if len(codes) > 1:
        out.append({"id": VARIANT + it.id, "label": f"{it.name}: rate-book item", "asks": f"Which rate-book item prices {it.name.lower()}?", "applies_to": [it.id], "read": None, "spec": None,
          "variant": {"item": it.id, "qty": qty},
          "options": {c: {"text": f"Rate-book item {c}", "spec_values": {}, "record": {}, "mrs_item": c, "mrs_ref": f"item {c}"} for c in codes}, "default": None})
  return out

def cards() -> tuple:
  return tuple([*_raw()["cards"], *variant_cards()])

def get(card_id: str) -> dict | None:
  return next((c for c in cards() if c["id"] == card_id), None)

def problems(data: dict | None = None, book_codes: set | None = None) -> list:
  from app.engine.catalogue import loader
  from app.modules.drawings_boq.pricing.billing import profiles as PF
  from app.engine.catalogue import param_keys as PK
  data = data or _raw()
  items = {i.id: i for i in loader.items()}
  specs = PF.spec_defaults()
  out, seen, owners = [], set(), {}
  q = data.get("use_defaults_question") or {}

  if q.get("id") != USE_DEFAULTS or set(q.get("options") or {}) != {"yes", "no"} or q.get("default") != "no":
    out.append("use_defaults_question must be USE_QS_DEFAULTS with the options yes and no and the default no: a project does not use QS defaults until it says so")
  for c in data["cards"]:
    name = c.get("id", "?")
    out += [f"{name}: no {f}" for f in CARD_FIELDS if f not in c]
    out += [f"{name}: repeated"] if name in seen else []
    seen.add(name)
    if name.startswith(VARIANT) or "." in str(name):
      out.append(f"{name}: an id has no dot and does not start with {VARIANT}")
    for i in c.get("applies_to") or []:
      if i not in items:
        out.append(f"{name}: {i} is not a catalogue item")
    if not c.get("applies_to"):
      out.append(f"{name}: applies_to lists no item")
    spec = c.get("spec")
    if spec is not None and spec not in specs:
      out.append(f"{name}: {spec} is not a billing spec (profiles.yaml spec_defaults)")
    if spec is not None:
      owners.setdefault(spec, []).append(name)
    read = c.get("read")
    if read is not None:
      key = PK.get(str(read.get("key")))
      if key is None or key["status"] != "LIVE":
        out.append(f"{name}: read key {read.get('key')} is not a live parameter key")
      elif read.get("scope") not in key["scopes"]:
        out.append(f"{name}: scope {read.get('scope')!r} is not a scope of {read['key']}")
      if not read.get("name"):
        out.append(f"{name}: a card that reads the drawing names what the printed value is called (read.name)")
      elif spec is not None and read["name"] != spec:
        out.append(f"{name}: the printed value is called {read['name']} but the card owns the spec {spec}")

    opts = c.get("options") or {}
    if len(opts) < 2:
      out.append(f"{name}: a card has at least two options")
    for val, o in opts.items():
      out += [f"{name} {val}: no {f}" for f in OPTION_FIELDS if f not in o]
      for sname in (o.get("spec_values") or {}):
        if sname != spec:
          out.append(f"{name} {val}: spec_values names {sname}, a card sets only the spec it owns ({spec})")
      code = o.get("mrs_item")
      if code is not None:
        if not CODE.match(str(code)):
          out.append(f"{name} {val}: {code} is not written like a rate-book item (6-6(a), 7-4)")
        elif book_codes is not None and code not in book_codes:
          out.append(f"{name} {val}: the rate book has no item {code}")
      elif not o.get("mrs_ref"):
        out.append(f"{name} {val}: with no mrs_item the option says where it sits in the rate book in mrs_ref")

    d = c.get("default")
    if d is not None:
      if d.get("value") not in opts:
        out.append(f"{name}: the default {d.get('value')!r} is not one of the options")
      if not d.get("source"):
        out.append(f"{name}: a default names its source: the QS and the date")
  for spec, names in owners.items():
    if len(names) > 1:
      out.append(f"{spec}: owned by {', '.join(names)}; billing has one {spec} for a project, so one card owns it and the others keep their value in record")
  for c in variant_cards():
    for val, o in c["options"].items():
      if book_codes is not None and o["mrs_item"] not in book_codes:
        out.append(f"{c['id']} {val}: the rate book has no item {o['mrs_item']}")
  return out

def use_qs_defaults(answers: dict | None) -> bool:
  got = (answers or {}).get(key_of(USE_DEFAULTS))
  return bool(got) and str(got.get("value") if isinstance(got, dict) else got) == YES

def _given(answers: dict | None, card_id: str):
  got = (answers or {}).get(key_of(card_id))
  return (got.get("value") if isinstance(got, dict) else got) if got else None

def printed_of(card: dict, printed: dict | None) -> str | None:
  read = card.get("read")
  if not read or not printed:
    return None
  got = ((printed.get("spec") or printed).get(read["key"]) or {}).get(read["scope"])
  return None if not got else str(got["value"] if isinstance(got, dict) else got)

def resolve(card: dict, printed: dict | None = None, answers: dict | None = None, use_defaults: bool | None = None) -> dict:
  opts = card["options"]
  value = printed_of(card, printed)
  if value is not None:
    name = card["read"]["name"]
    return {"state": PRINTED, "value": value, "option": None, "spec_values": {name: value} if name == card.get("spec") else {}, "record": {name: value}, "mrs_item": None, "basis": "PRINTED"}
  given = _given(answers, card["id"])

  if given in opts:
    o = opts[given]
    return {"state": DECIDED, "value": given, "option": o, "spec_values": dict(o["spec_values"]), "record": dict(o["record"]), "mrs_item": o["mrs_item"], "basis": "ANSWER"}
  use = use_qs_defaults(answers) if use_defaults is None else use_defaults
  d = card.get("default")
  if use and d and d["value"] in opts:
    o = opts[d["value"]]
    return {"state": DEFAULT, "value": d["value"], "option": o, "spec_values": dict(o["spec_values"]), "record": dict(o["record"]), "mrs_item": o["mrs_item"], "basis": "ASSUMED"}
  return {"state": OPEN, "value": None, "option": None, "spec_values": {}, "record": {}, "mrs_item": None, "basis": None}

def decisions(answers: dict | None, printed: dict | None = None, base: dict | None = None, use_defaults: bool | None = None) -> dict:
  out = {k: (dict(v) if isinstance(v, dict) else v) for k, v in (base or {}).items()}
  basis = dict(out.get("basis") or {})
  items = dict(out.get("billing_item") or {})
  for c in cards():
    got = resolve(c, printed, answers, use_defaults)
    if got["state"] == OPEN:
      continue
    for name, value in got["spec_values"].items():
      if name not in (base or {}):
        out[name] = value
        basis[name] = got["basis"]
    if got["mrs_item"]:
      for it in c["applies_to"]:
        items.setdefault(it, got["mrs_item"])
  if basis:
    out["basis"] = basis
  if items:
    out["billing_item"] = items
  return out

def billing_items(answers: dict | None, printed: dict | None = None, use_defaults: bool | None = None) -> dict:
  return dict(decisions(answers, printed, None, use_defaults).get("billing_item") or {})

def open_cards(answers: dict | None, printed: dict | None = None, use_defaults: bool | None = None) -> list:
  return [c for c in cards() if resolve(c, printed, answers, use_defaults)["state"] == OPEN]

def main() -> int:
  bad = problems()
  mapped = sum(1 for c in cards() for o in c["options"].values() if o["mrs_item"])
  total = sum(len(c["options"]) for c in cards())
  print("\n".join(bad) if bad else f"{len(cards())} cards ({len(_raw()['cards'])} asked and {len(variant_cards())} of rate-book item), 0 problems; {mapped} of {total} options name a rate-book item")
  return 1 if bad else 0

if __name__ == "__main__":
  import sys
  sys.exit(main())
