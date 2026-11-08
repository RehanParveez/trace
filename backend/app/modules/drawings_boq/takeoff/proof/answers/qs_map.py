from __future__ import annotations
import argparse
import asyncio
import json
import os
import re
import sys
import yaml
from app.engine.catalogue import loader as CL
from app.modules.drawings_boq.takeoff.ai_reader import cache as CACHE
from app.modules.drawings_boq.takeoff.ai_reader import candidate as CAND
from app.modules.drawings_boq.takeoff.ai_reader import evidence as EV
from app.modules.drawings_boq.takeoff.ai_reader import prompts as PR
from app.modules.drawings_boq.takeoff.ai_reader import tasks as TASKS
from app.modules.drawings_boq.takeoff.proof import case_io as CIO
from app.engine.catalogue import vocabulary as V
from app.modules.drawings_boq.takeoff.proof.answers import answers as AN
from app.modules.drawings_boq.takeoff.proof.answers import qs_import as QI

HERE = os.path.dirname(os.path.abspath(__file__))
MAP_PATH = os.path.join(HERE, "qs_map.yaml")
REVIEW = "answers_review.yaml"
AI_FOLDER = "answers_ai"
TASK = "VOCAB"
PARTIAL_RATIO = 0.6
MAX_SPECIFIC = 3
CHOICES_LIMIT = 40
UNIT_CLASS = {"cft": "volume", "m3": "volume", "sft": "area", "m2": "area", "rft": "length", "m": "length", "kg": "weight", "ton": "weight", "nos": "count", "ls": "lump", "lump_sum": "lump"}
CATALOGUE, PERSON, AI, VOCAB, MAP_SKIP = "CATALOGUE", "PERSON", "AI", "VOCAB", "SKIP"

def norm_key(raw) -> str:
  return V.norm(raw)

def load_map(path: str = MAP_PATH) -> dict:
  if not os.path.isfile(path):
    return {"qs": {}}
  with open(path, encoding="utf-8") as fh:
    data = yaml.safe_load(fh) or {}
  data.setdefault("qs", {})
  return data

def save_map(data: dict, path: str = MAP_PATH) -> None:
  with open(path, "w", encoding="utf-8", newline="\n") as fh:
    yaml.safe_dump({"qs": {q: {k: v for k, v in sorted(m.items())} for q, m in sorted(data["qs"].items())}}, fh, sort_keys=False, allow_unicode=True, width=1000)

class Index:
  def __init__(self, vocab: dict):
    self.vocab = vocab
    self.stop = set(vocab.get("stopwords") or [])
    self.syn = [(re.compile(s["pattern"], re.I), s["to"]) for s in vocab.get("synonyms") or []]
    self.items = [i for i in CL.items()]
    self.order = {i.id: n for n, i in enumerate(self.items)}
    self.names = {i.id: self.tokens(i.name) for i in self.items}
    self.by_id = {i.id: i for i in self.items}

  def tokens(self, raw: str) -> set:
    t = " " + str(raw or "").lower() + " "
    for rx, to in self.syn:
      t = rx.sub(f" {to} ", t)
    out = set()
    for w in re.findall(r"[a-z]{2,}", t):
      if w in self.stop:
        continue
      out.add(w[:-1] if len(w) > 3 and w.endswith("s") and not w.endswith("ss") else w)
    return out

  def unit_class(self, unit) -> str | None:
    return UNIT_CLASS.get(str(unit or "").lower())

  def ranked(self, ids: list, unit) -> list:
    cls = self.unit_class(unit)
    def rank(i):
      it = self.by_id[i]
      return (0 if it.billing.PRIVATE_QS else 1, 0 if cls and self.unit_class(it.unit) == cls else 1, self.order[i])
    return sorted(ids, key=rank)

  def want_of(self, raw: str, unit=None) -> set:
    want = self.tokens(raw)
    implied = (self.vocab.get("implied_by_unit") or {}).get(self.unit_class(unit))
    return want | self.tokens(implied) if implied and want else want

  def match(self, raw: str, unit=None) -> dict:
    want = self.want_of(raw, unit)
    if not want:
      return {"ids": [], "how": None}
    pool = [i.id for i in self.items if self.unit_class(unit) != "weight" or self.unit_class(i.unit) == "weight"]
    whole = [i for i in pool if want <= self.names[i]]
    if whole:
      return {"ids": self.ranked(whole, unit), "how": "name"}
    part = [i for i in pool if len(want & self.names[i]) / len(want) >= PARTIAL_RATIO and len(want & self.names[i]) >= min(2, len(want))]
    if part:
      best = max(len(want & self.names[i]) for i in part)
      part = [i for i in part if len(want & self.names[i]) == best]
      return {"ids": self.ranked(part, unit), "how": "partial"}
    return {"ids": [], "how": None}

  def choices_for(self, raw: str, unit=None) -> list:
    want = self.tokens(raw)
    score: dict = {}
    for i in self.items:
      score[i.section] = score.get(i.section, 0) + len(want & self.names[i.id])
    cls = self.unit_class(unit)
    for sec in sorted(score, key=lambda s: -score[s]):
      pool = [i.id for i in self.items if i.section == sec]
      if score[sec] > 0:
        return self.ranked(pool, unit)[:CHOICES_LIMIT]
    pool = [i.id for i in self.items if cls and self.unit_class(i.unit) == cls]
    return self.ranked(pool, unit)[:CHOICES_LIMIT]

def row_keys(row: dict) -> list:
  item = row.get("item") or ""
  groups = row.get("groups") or []
  if row["role"] == QI.BILL_ITEM or row["role"] == QI.SUMMARY and not item:
    return [norm_key(row.get("description"))]
  keys = []
  if groups:
    keys.append(norm_key(f"{item} | {groups[-1]}"))
  keys.append(norm_key(item or row.get("description")))
  return [k for k in keys if k]

def row_texts(row: dict) -> list:
  item = row.get("item") or ""
  groups = row.get("groups") or []
  if row["role"] in (QI.BILL_ITEM,) or (row["role"] == QI.SUMMARY and not item):
    return [str(row.get("description") or "")]
  base = item or str(row.get("description") or "")
  if groups:
    return [f"{base} {groups[-1]}", base, groups[-1]]
  return [base]

def line_text(row: dict) -> str:
  item = row.get("item") or ""
  groups = row.get("groups") or []
  if row["role"] in (QI.BILL_ITEM,) or (row["role"] == QI.SUMMARY and not item):
    return str(row.get("description") or "")
  return f"{item} | {groups[-1]}" if groups else (item or str(row.get("description") or ""))

def resolve(row: dict, qs_map: dict, index: Index, ai: dict) -> dict:
  keys = row_keys(row)
  for k in keys:
    hit = qs_map.get(k)
    if hit:
      if hit.get("skip"):
        return {"element": None, "mapped_by": PERSON, "confirmed": True, "key": k, "reason": hit.get("note") or "marked by the QS map as not a catalogue item", "skip": True}
      return {"element": hit["element"], "mapped_by": PERSON, "confirmed": True, "key": k, "floor": hit.get("floor")}
  for k in keys:
    got = V.item_for(k)
    if got:
      return {"element": got, "mapped_by": VOCAB, "confirmed": True, "key": k}
  for k in keys:
    if k in ai:
      a = ai[k]
      return {"element": a["element"], "mapped_by": AI, "confirmed": False, "key": k, "reason": a.get("reason")}
  unit = row.get("unit")
  texts = row_texts(row)
  
  tried = [(t, index.match(t, unit)) for t in texts]
  chosen = next(((t, g) for t, g in tried if g["ids"] and len(g["ids"]) <= MAX_SPECIFIC), None)
  chosen = chosen or next(((t, g) for t, g in reversed(tried[:2]) if g["ids"]), None) or next(((t, g) for t, g in tried if g["ids"]), None)
  if chosen is None:
    return {"element": None, "mapped_by": None, "confirmed": False, "key": keys[-1], "reason": "no catalogue item has the words of this line"}
  text, got = chosen
  item_only = tried[1][1] if len(tried) > 1 else tried[0][1]
  same_as_item = len(keys) > 1 and (text == texts[1] or (item_only["ids"] and item_only["ids"][0] == got["ids"][0]))
  key = keys[-1] if len(keys) == 1 or same_as_item else keys[0]
  return {"element": got["ids"][0], "mapped_by": CATALOGUE, "confirmed": False, "key": key, "candidates": got["ids"][:6], "how": got["how"], "ambiguous": len(got["ids"]) > 1}

def ai_path(case_dir: str, cache_key: str) -> str:
  return os.path.join(case_dir, AI_FOLDER, cache_key + ".json")

def ai_cache_key(sha: str, line: str, unit, model: str, version: str) -> str:
  return CACHE.key(sha, 0, {"kind": "TEXT", "line": norm_key(line), "unit": str(unit or "")}, TASK, version, model)

def read_ai(case_dir: str) -> dict:
  out: dict = {}
  folder = os.path.join(case_dir, AI_FOLDER)
  if not os.path.isdir(folder):
    return out
  for name in sorted(os.listdir(folder)):
    if not name.endswith(".json"):
      continue
    with open(os.path.join(folder, name), encoding="utf-8") as fh:
      e = json.load(fh)
    if e.get("candidate", {}).get("status") in (CAND.CANDIDATE, CAND.SHADOW) and e.get("answer", {}).get("element"):
      out.setdefault(e["key"], {"element": e["answer"]["element"], "reason": e["answer"].get("reason"), "cache_key": e["cache_key"]})
  return out

async def ask_one(case_dir: str, sha: str, key: str, line: str, unit, choices: list, index: Index, provider, model: str, max_tokens: int, timeout_s):
  from app.modules.ai_requests.service import AIOrchestratorService
  version = PR.load(TASKS.get(TASK).prompt)["version"]
  ck = ai_cache_key(sha, line, unit, model, version)
  if os.path.isfile(ai_path(case_dir, ck)):
    return "cached", ck
  
  listing = "\n".join(f"{i} | {index.by_id[i].name} | {index.by_id[i].unit}" for i in choices)
  prompt = PR.render(TASKS.get(TASK).prompt, line=line, unit=str(unit or "?"), choices=listing)
  raw, parsed, usage = await AIOrchestratorService._call_provider(provider, model, prompt, [], max_tokens, timeout_s)
  answer = parsed if isinstance(parsed, dict) else {}
  element = answer.get("element")
  validators = [EV.choice_offered(element, choices), EV.result("reason_given", bool(str(answer.get("reason") or "").strip()), "a reason is given" if str(answer.get("reason") or "").strip() else "no reason is given")]
  cand = CAND.build(task=TASK, page=0, value={"element": element, "reason": answer.get("reason")}, quotes=[line], bbox=None, confidence=None, model=model, prompt=prompt,
    prompt_version=version, cache_key=ck, validators=validators, shadow=False, input_tokens=(usage or {}).get("input_tokens"), output_tokens=(usage or {}).get("output_tokens"))
  entry = {"cache_key": ck, "task": TASK, "key": key, "line": line, "unit": unit, "model": model, "answer": {"element": element, "reason": answer.get("reason")}, "validators": validators, "candidate": cand, "choices": choices}
  os.makedirs(os.path.dirname(ai_path(case_dir, ck)), exist_ok=True)
  with open(ai_path(case_dir, ck), "w", encoding="utf-8", newline="\n") as fh:
    json.dump(entry, fh, indent=2, sort_keys=True, ensure_ascii=False)
    fh.write("\n")
  return "asked", ck

def ask_all(case_dir: str, sha: str, wanted: list, index: Index, where: str, model: str | None) -> dict:
  from app.modules.ai_requests.service import CONSENT_PROVIDER, DEFAULT_MAX_TOKENS, model_of
  provider = CONSENT_PROVIDER["LOCAL" if where == "local" else "OUTSIDE"]
  model = model or model_of(provider)
  stats = {"asked": 0, "cached": 0, "failed": 0}

  async def run():
    for key, line, unit in wanted:
      try:
        state, _ = await ask_one(case_dir, sha, key, line, unit, index.choices_for(line, unit), index, provider, model, DEFAULT_MAX_TOKENS, None)
        stats[state] += 1
      except Exception as exc:
        stats["failed"] += 1
        print(f"{key}: failed: {exc}", file=sys.stderr)
  asyncio.run(run())
  return stats

def rows_text(rows: list) -> str:
  nums = sorted(r["row"] for r in rows)
  spans, start, prev = [], None, None
  for n in nums:
    if start is None:
      start = prev = n
    elif n == prev + 1:
      prev = n
    else:
      spans.append((start, prev))
      start = prev = n
  if start is not None:
    spans.append((start, prev))
  return ",".join(str(a) if a == b else f"{a}-{b}" for a, b in spans)

def build(imp: dict, qs_map: dict, index: Index, ai: dict, qs_id: str, case_name: str) -> dict:
  resolved: dict = {}
  groups: dict = {}
  unmapped: dict = {}
  summary_groups: dict = {}
  for row in imp["rows"]:
    if row["kind"] == QI.NO_QUANTITY:
      k = ("NOQ", row["sheet"], norm_key(row.get("description")), row.get("unit"))
      g = unmapped.setdefault(k, {"qs_line": row.get("description"), "sheet": row["sheet"], "unit": row.get("unit"), "quantity": None, "rows": [], "reason": "the workbook gives no quantity for this line"})
      g["rows"].append(row)
      continue
    if row["kind"] != QI.MEASURED:
      continue
    
    rk = (row["sheet"], tuple(row_keys(row)), row.get("unit"))
    if rk not in resolved:
      resolved[rk] = resolve(row, qs_map, index, ai)
    res = resolved[rk]
    target = summary_groups if row["role"] == QI.SUMMARY else groups
    if res.get("element") is None:
      if row["role"] == QI.SUMMARY:
        continue
      k = ("UNM", row["sheet"], res["key"], row.get("unit"))
      reason = res.get("reason") or "no catalogue item has these words"
      g = unmapped.setdefault(k, {"qs_line": line_text(row), "sheet": row["sheet"], "unit": row.get("unit"), "quantity": 0.0, "rows": [], "reason": reason, "key": res["key"]})
      g["quantity"] += row["quantity"]
      g["rows"].append(row)
      g["skip"] = bool(res.get("skip"))
      continue
    
    floor = res.get("floor") or row.get("floor")
    k = (res["element"], floor, row.get("unit"), line_text(row), row["sheet"])
    g = target.setdefault(k, {"element": res["element"], "floor": floor, "unit": row.get("unit"), "qs_line": line_text(row), "sheet": row["sheet"], "quantity": 0.0, "rows": [],
      "mapped_by": res["mapped_by"], "confirmed": res["confirmed"], "key": res["key"], "res": res})
    g["quantity"] += row["quantity"]
    g["rows"].append(row)
  items = [{"element": g["element"], "floor": g["floor"], "quantity": round(g["quantity"], 6), "unit": g["unit"], "qs_line": g["qs_line"], "sheet": g["sheet"], "rows": rows_text(g["rows"]), "mapped_by": g["mapped_by"], "confirmed": g["confirmed"]}
    for _k, g in sorted(groups.items(), key=lambda kv: (kv[0][0], str(kv[0][1]), kv[0][3], kv[0][4]))]
  unm = [{"qs_line": g["qs_line"], "quantity": None if g["quantity"] is None else round(g["quantity"], 6), "unit": g["unit"], "sheet": g["sheet"], "rows": rows_text(g["rows"]), "reason": g["reason"]}
    for _k, g in sorted(unmapped.items(), key=lambda kv: (kv[0][1], str(kv[0][2])))]
  compare: dict = {}
  for g in groups.values():
    compare.setdefault((g["element"], g["unit"]), [0.0, 0.0])[0] += g["quantity"]
  for g in summary_groups.values():
    compare.setdefault((g["element"], g["unit"]), [0.0, 0.0])[1] += g["quantity"]
  check = [{"element": e, "unit": u, "detail": round(a, 4), "summary": round(b, 4), "difference": round(a - b, 4)} for (e, u), (a, b) in sorted(compare.items(), key=lambda kv: str(kv[0])) if a and b and abs(a - b) > 1e-6 * max(1.0, abs(b))]
  reviews = review_rows(groups, unmapped, summary_groups, index)
  return {"items": items, "unmapped_lines": unm, "summary_check": check, "reviews": reviews}

def review_rows(groups: dict, unmapped: dict, summary_groups: dict, index: Index) -> list:
  by_key: dict = {}
  for k, g in list(groups.items()):
    if g["confirmed"]:
      continue
    e = by_key.setdefault(g["key"], {"key": g["key"], "qs_line": g["qs_line"], "sheets": set(), "rows": 0, "quantity": {}, "mapped_by": g["mapped_by"], "element": g["element"], "res": g["res"]})
    e["sheets"].add(g["sheet"])
    e["rows"] += len(g["rows"])
    e["quantity"][g["unit"] or "?"] = e["quantity"].get(g["unit"] or "?", 0.0) + g["quantity"]
  for k, g in unmapped.items():
    if k[0] != "UNM" or g.get("skip"):
      continue
    e = by_key.setdefault(g["key"], {"key": g["key"], "qs_line": g["qs_line"], "sheets": set(), "rows": 0, "quantity": {}, "mapped_by": None, "element": None, "res": {}})
    e["sheets"].add(g["sheet"])
    e["rows"] += len(g["rows"])
    e["quantity"][g["unit"] or "?"] = e["quantity"].get(g["unit"] or "?", 0.0) + (g["quantity"] or 0.0)
  out = []
  for key, e in sorted(by_key.items(), key=lambda kv: (-kv[1]["rows"], kv[0])):
    it = index.by_id.get(e["element"]) if e["element"] else None
    out.append({"key": key, "qs_line": e["qs_line"], "sheets": sorted(e["sheets"]), "rows": e["rows"], "quantity": {u: round(q, 4) for u, q in e["quantity"].items()}, "mapped_by": e["mapped_by"],
      "element": e["element"], "name": it.name if it else None, "candidates": [f"{c} {index.by_id[c].name}" for c in (e["res"].get("candidates") or [])], "reason": e["res"].get("reason"), "confirmed": False})
  return out

def percentages(items: list, unmapped: list, imp: dict) -> dict:
  rows = {"PERSON": 0, "VOCAB": 0, "CATALOGUE": 0, "AI": 0, "unmapped": 0}
  for it in items:
    n = sum(b - a + 1 for a, b in ((int(x.split("-")[0]), int(x.split("-")[-1])) for x in it["rows"].split(",") if x))
    rows[it["mapped_by"]] += n
  for u in unmapped:
    rows["unmapped"] += sum(b - a + 1 for a, b in ((int(x.split("-")[0]), int(x.split("-")[-1])) for x in u["rows"].split(",") if x))
  return rows

def case_paths(case_name: str, cases_dir: str | None) -> dict:
  folder = os.path.join(CIO.HERE, case_name)
  return {"folder": folder, "answers": os.path.join(folder, AN.FILE), "review": os.path.join(folder, REVIEW)}

def run_map(case_name: str, qs_id: str | None, cases_dir: str | None, ai_where: str | None, ai_model: str | None, map_path: str = MAP_PATH) -> dict:
  case, wb_path, block_floor = QI.case_workbook(case_name, cases_dir)
  if not os.path.isfile(wb_path):
    raise FileNotFoundError(f"The workbook is not at {wb_path}.")
  paths = case_paths(case_name, cases_dir)
  if qs_id is None:
    qs_id = (AN.read_yaml(paths["review"]) or {}).get("qs") or case_name
  vocab = QI.vocabulary()
  imp = QI.read_workbook(wb_path, block_floor, vocab)
  index = Index(vocab)
  data = load_map(map_path)
  qs_map = data["qs"].get(qs_id) or {}
  ai = read_ai(paths["folder"])
  stats = None
  
  if ai_where:
    first = build(imp, qs_map, index, ai, qs_id, case_name)
    wanted = []
    seen = set()
    for r in first["reviews"]:
      if r["element"] and r["mapped_by"] == CATALOGUE and not r["candidates"][1:]:
        continue
      if r["key"] in seen:
        continue
      seen.add(r["key"])
      wanted.append((r["key"], r["qs_line"], next(iter(r["quantity"]), None)))
    stats = ask_all(paths["folder"], imp["sha256"], wanted, index, ai_where, ai_model)
    ai = read_ai(paths["folder"])
  res = build(imp, qs_map, index, ai, qs_id, case_name)
  doc = AN.document(case_name, imp, qs_id, res)
  AN.write_yaml(paths["answers"], doc)
  AN.write_yaml(paths["review"], {"qs": qs_id, "workbook": imp["workbook"], "how_to": "For each entry set confirmed: true when the element is right, or write the right element id (and confirmed: true), or write skip: true with a note when the line is not a catalogue item. Then run: python -m app.modules.drawings_boq.takeoff.proof.answers.qs_map fold " + case_name, "mappings": res["reviews"]})
  return {"imp": imp, "result": res, "qs": qs_id, "ai": stats, "paths": paths}

def run_fold(case_name: str, cases_dir: str | None, map_path: str = MAP_PATH) -> dict:
  paths = case_paths(case_name, cases_dir)
  review = AN.read_yaml(paths["review"])
  if not review:
    raise FileNotFoundError(f"There is no {REVIEW} for {case_name}; run map first.")
  data = load_map(map_path)
  mp = data["qs"].setdefault(review["qs"], {})
  index = Index(QI.vocabulary())
  added = skipped = bad = 0
  for m in review.get("mappings") or []:
    if m.get("skip") and m.get("confirmed"):
      mp[m["key"]] = {"skip": True, "note": str(m.get("note") or ""), **{k: m[k] for k in ("confirmed_by", "confirmed_date") if m.get(k)}}
      added += 1
      continue
    if not m.get("confirmed"):
      skipped += 1
      continue
    if not m.get("element") or m["element"] not in index.by_id:
      bad += 1
      print(f"{m['key']}: confirmed but {m.get('element')!r} is not a catalogue item; left out.", file=sys.stderr)
      continue
    mp[m["key"]] = {"element": m["element"], **{k: m[k] for k in ("floor", "confirmed_by", "confirmed_date") if m.get(k)}}
    added += 1
  save_map(data, map_path)
  return {"added": added, "left": skipped, "bad": bad, "qs": review["qs"], "size": len(mp)}

def lines_of(out: dict) -> list:
  imp, res = out["imp"], out["result"]
  p = percentages(res["items"], res["unmapped_lines"], imp)
  total = sum(p.values()) or 1
  lines = [f"{imp['workbook']} for QS {out['qs']}: {len(res['items'])} answer items, {len(res['unmapped_lines'])} unmapped lines, {len(res['reviews'])} mappings to confirm",
    "  measured rows by how they were mapped: " + ", ".join(f"{k} {v} ({v * 100 / total:.0f}%)" for k, v in p.items())]
  for d in QI.totals_check(imp):
    lines.append(f"  TOTAL DIFFERS {d['sheet']!r} rows {d['rows']}: summed {d['summed']:.4f}, workbook says {d['workbook']:.4f}, difference {d['difference']:.4f}")
  for d in res["summary_check"]:
    lines.append(f"  detail vs summary {d['element']} {d['unit']}: rows sum to {d['detail']}, summary lines say {d['summary']}, difference {d['difference']}")
  if out["ai"]:
    lines.append(f"  AI: {out['ai']['asked']} asked, {out['ai']['cached']} already cached, {out['ai']['failed']} failed")
  return lines

def main(argv: list | None = None) -> int:
  ap = argparse.ArgumentParser(description="Map the lines of a QS workbook to catalogue items, write the case's answers.yaml and answers_review.yaml, or fold confirmed mappings into qs_map.yaml.")
  sub = ap.add_subparsers(dest="cmd", required=True)
  m = sub.add_parser("map")
  m.add_argument("case")
  m.add_argument("--qs", default=None, help="the QS this workbook comes from; the confirmed map is kept per QS (default: the one in the case's review file, else the case name)")
  m.add_argument("--cases-dir", default=None)
  m.add_argument("--ai", choices=("local", "outside"), default=None, help="ask a model about the lines the catalogue cannot place; answers are kept as candidates in the case's answers_ai folder")
  m.add_argument("--model", default=None)
  f = sub.add_parser("fold")
  f.add_argument("case")
  f.add_argument("--cases-dir", default=None)
  ex = sub.add_parser("export", help="write the mappings still to confirm as an xlsx (line, quantity, proposed item, five candidate items, floor) for the QS")
  ex.add_argument("case")
  ex.add_argument("--out", default="mapping_out")
  im = sub.add_parser("import", help="read the QS's decisions back; with --write they go to answers_review.yaml and, folded, to qs_map.yaml under the QS's name")
  im.add_argument("case")
  im.add_argument("workbook")
  im.add_argument("--by", required=True, help="the person who confirmed; the AI cannot")
  im.add_argument("--write", action="store_true")
  rj = sub.add_parser("rejected", help="the proposals the QS changed, with what the mapper proposed and who proposed it")
  rj.add_argument("case")

  args = ap.parse_args(argv)
  
  if args.cmd in ("export", "import", "rejected"):
    from app.modules.drawings_boq.takeoff.proof.answers import sheet as SH
    return {"export": SH.cmd_export, "import": SH.cmd_import, "rejected": SH.cmd_rejected}[args.cmd](args)
  if args.cmd == "fold":

    r = run_fold(args.case, args.cases_dir)
    print(f"QS {r['qs']}: {r['added']} mapping(s) folded into qs_map.yaml, {r['left']} not confirmed yet, {r['bad']} refused; the map now holds {r['size']}.")
    return 0 if not r["bad"] else 1
  out = run_map(args.case, args.qs, args.cases_dir, args.ai, args.model)
  for ln in lines_of(out):
    print(ln)
  return 0

if __name__ == "__main__":
  sys.exit(main())
