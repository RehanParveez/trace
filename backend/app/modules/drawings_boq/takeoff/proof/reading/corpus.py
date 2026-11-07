from __future__ import annotations
import json
import os
import yaml
from app.modules.drawings_boq.takeoff.proof import case_io as CIO
from app.modules.drawings_boq.takeoff.proof.reading import formats as F
from app.modules.drawings_boq.takeoff.proof.reading import score as SCR
from app.modules.drawings_boq.takeoff.proof.reading import sets as S
from app.modules.drawings_boq.takeoff.run import vocab as V

HERE = os.path.dirname(os.path.abspath(__file__))
CORPUS = os.path.join(HERE, "corpus.md")
FACTS = os.path.join(HERE, "corpus_facts.yaml")
TARGET_CONSULTANTS = 8
FACT_KEYS = ("plot_size", "storeys", "city", "companions")
UNITS = ("FT_IN", "MM")

def load_facts(path: str = FACTS) -> dict:
  if not os.path.isfile(path):
    return {}
  with open(path, encoding="utf-8") as fh:
    return yaml.safe_load(fh) or {}

def save_facts(facts: dict, path: str = FACTS) -> None:
  with open(path, "w", encoding="utf-8", newline="\n") as fh:
    yaml.safe_dump(facts, fh, sort_keys=True, allow_unicode=True)

def _first_sight(folder: str) -> dict | None:
  path = os.path.join(folder, "first_sight.json")
  if not os.path.isfile(path):
    return None
  with open(path, encoding="utf-8") as fh:
    return json.load(fh)

def _dominant(counts: dict) -> str | None:
  return max(sorted(counts), key=lambda k: counts[k]) if counts else None

def _text_type(ts: F.TruthSet, fs: dict | None) -> str | None:
  if fs and (fs.get("profile") or {}).get("text_types"):
    return _dominant(fs["profile"]["text_types"])
  counts: dict = {}
  for r in ts.register:
    counts[r.text_type.value] = counts.get(r.text_type.value, 0) + 1
  return _dominant(counts)

def _score_of(alias: str, score_doc: dict | None) -> str:
  if not score_doc:
    return "-"
  rows = [o for o in score_doc.get("outcomes") or [] if o["set"] == alias]
  t = SCR._tally(rows)
  if not t["truth"]:
    return "no truth yet"
  lo, hi = t["recall_ci"]
  return f"{t['matched']} of {t['truth']} read ({t['recall']:.0%}; Wilson 95% interval {lo:.0%} to {hi:.0%})"

def rows_of(cases_dir: str | None = None, root: str = CIO.HERE, score_doc: dict | None = None) -> list:
  facts = load_facts()
  refs = [r for r in S.find_sets(cases_dir, root) if not r.link]
  out = []
  for ref in refs:
    ts = F.load_set(ref.truth_folder)
    d = ts.document
    fs = _first_sight(ref.truth_folder)
    mine = facts.get(d.alias) or {}
    siblings = [r.pdf for r in refs if r.case == ref.case and r.pdf != ref.pdf]
    out.append({"alias": d.alias, "consultant": d.consultant, "producer": d.producer, "text_type": _text_type(ts, fs), "plot_size": mine.get("plot_size"), "storeys": mine.get("storeys"),
      "city": mine.get("city"), "units": d.units, "companions": mine.get("companions") or (", ".join(siblings) if siblings else None), "split": d.split.value.lower(), "pages": d.pages,
      "first_sight": ("" if fs else "current engine, no first sight stored: ") + _score_of(d.alias, score_doc) if d.split == V.Split.HELDOUT else "-", "recorded": bool(fs)})
  return out

def gaps_of(rows: list) -> list:
  out = []
  named = sorted({r["consultant"] for r in rows if r["consultant"]})
  out.append(f"Consultants: {len(named)} named of the {TARGET_CONSULTANTS} the build file asks for ({len(named)} / {TARGET_CONSULTANTS}); {TARGET_CONSULTANTS - len(named)} more needed." if len(named) < TARGET_CONSULTANTS else f"Consultants: {len(named)}, target {TARGET_CONSULTANTS} met.")
  blank = sorted(r["alias"] for r in rows if not r["consultant"])
  if blank:
    out.append(f"Consultant not recorded for: {', '.join(blank)}.")
  types = {r["text_type"] for r in rows if r["text_type"]}
  want = {t.value for t in V.TextType}
  out.append("Text types not yet seen in any set: " + (", ".join(sorted(want - types)) or "none") + ". (The list of types is the vocabulary of the benchmark; the benchmark guide section 7 was not available when this was written.)")
  units = {r["units"] for r in rows if r["units"] not in (None, "UNKNOWN")}
  out.append("Units not yet seen: " + (", ".join(u for u in UNITS if u not in units) or "none") + ("; units UNKNOWN for " + ", ".join(sorted(r["alias"] for r in rows if r["units"] in (None, "UNKNOWN"))) if any(r["units"] in (None, "UNKNOWN") for r in rows) else "") + ".")
  producers = sorted({r["producer"] for r in rows if r["producer"]})
  out.append(f"Producers seen: {len(producers)} ({', '.join(producers) or 'none'}); the build file gives no target.")
  for key, label in (("plot_size", "Plot sizes"), ("storeys", "Storeys"), ("city", "Cities")):
    have = sorted({str(r[key]) for r in rows if r[key]})
    missing = sorted(r["alias"] for r in rows if not r[key])
    out.append(f"{label}: {len(have)} distinct recorded ({', '.join(have) or 'none'}); not recorded for {len(missing)} of {len(rows)} sets. Fill `corpus_facts.yaml`.")
  held = [r for r in rows if r["split"] == "heldout"]
  out.append(f"Held-out sets: {len(held)}; with a recorded first sight: {sum(r['recorded'] for r in held)}.")
  return out

RULES = ("\n## Rules\n\n- A new set comes in through `proof.reading intake` as held out; its first sight is stored in `first_sight.json` and never overwritten.\n"
  "- `proof.reading score --split heldout` is the number a release quotes; quote it with its Wilson interval. A score on one or two new sets is noisy.\n"
  "- `proof.reading first-sight-check` says whether the engine still reads a held-out set as it did at first sight; if it has moved, the held-out score is no longer the first-sight score.\n"
  "- Promotion: a held-out set moves to dev only in a pack that tunes on it, and that pack's md says so. The held-out pool is then refilled from the next intake.\n"
  "- A PDF already in the corpus (same sha256) is refused by intake, with the existing alias shown.\n")

def render(rows: list) -> str:
  head = "| Alias | Consultant | Producer | Text type | Plot size | Storeys | City | Units | Companions | Split | Pages | First-sight score |\n|---|---|---|---|---|---|---|---|---|---|---|---|\n"
  def cell(v):
    return "-" if v in (None, "") else str(v).replace("|", "/")
  body = "".join("| " + " | ".join(cell(r[k]) for k in ("alias", "consultant", "producer", "text_type", "plot_size", "storeys", "city", "units", "companions", "split", "pages", "first_sight")) + " |\n" for r in rows)
  gaps = "".join(f"- {g}\n" for g in gaps_of(rows))
  return ("# Reading benchmark corpus\n\nOne row per set. Written by `proof.reading corpus` (and by `proof.reading intake`); do not edit the table by hand. "
    "Plot size, storeys, city and companions come from `corpus_facts.yaml`, which you edit.\n\n" + head + body + "\n## Gaps against the variety targets\n\n" + gaps + RULES)

def write(cases_dir: str | None = None, root: str = CIO.HERE, score_json: str | None = None) -> str:
  doc = None
  if score_json and os.path.isfile(score_json):
    with open(score_json, encoding="utf-8") as fh:
      doc = json.load(fh)
  text = render(rows_of(cases_dir, root, doc))
  with open(CORPUS, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(text)
  return CORPUS
