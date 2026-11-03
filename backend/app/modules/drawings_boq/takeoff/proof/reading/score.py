from __future__ import annotations
import hashlib
import json
import math
import os
import yaml
from app.modules.drawings_boq.takeoff.proof.reading import vocab as V
from app.modules.drawings_boq.takeoff.proof.reading import match as M
from app.modules.drawings_boq.takeoff.proof.reading import sets as S
from app.modules.drawings_boq.takeoff.proof.reading import formats as F
from app.modules.drawings_boq.takeoff.proof.reading import adapter as AD
from app.modules.drawings_boq.takeoff.proof import case_io as CIO

HERE = os.path.dirname(os.path.abspath(__file__))
BASELINE = os.path.join(HERE, "baseline.json")
ACCEPTED = os.path.join(HERE, "accepted_regressions.yaml")
OK, WRONG, MISSED_S, MISSED_R = (V.OutcomeTruth.MATCHED_OK.value, V.OutcomeTruth.MATCHED_WRONG_VALUE.value, V.OutcomeTruth.MISSED_SILENT.value, V.OutcomeTruth.MISSED_REPORTED.value)
TRUE, INV_S, INV_F = V.OutcomeRead.TRUE.value, V.OutcomeRead.INVENTED_SILENT.value, V.OutcomeRead.INVENTED_FLAGGED.value
FACT_OUTCOME = {"PASS": OK, "FAIL": WRONG, "MISSING": MISSED_S}
REGISTER_FIELDS = ("sheet_no", "title", "role", "plan_kind", "floor", "discipline", "scale_ratio", "scale_basis", "text_type")
TRUTH_SIDE = (OK, WRONG, MISSED_S, MISSED_R)

def wilson(k: int, n: int) -> tuple:
  if n <= 0:
    return (None, None)
  z = M.rules()["wilson_z"]
  p = k / n
  d = 1 + z * z / n
  centre = (p + z * z / (2 * n)) / d
  half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
  return (round(max(0.0, centre - half), 4), round(min(1.0, centre + half), 4))

def _digest(paths: list) -> str:
  h = hashlib.sha256()
  for p in paths:
    if os.path.isfile(p):
      h.update(os.path.relpath(p, CIO.HERE).replace("\\", "/").encode())
      h.update(open(p, "rb").read().replace(b"\r\n", b"\n"))
  return h.hexdigest()

def truth_fingerprint(root: str = CIO.HERE) -> str:
  paths = []
  for ref in S.find_sets(root=root):
    if not ref.link:
      paths += [os.path.join(ref.truth_folder, n) for n in F.FILES]
    paths.append(os.path.join(root, ref.case, "facts.yaml"))
  return _digest(sorted(set(paths)))

def _outcome(oid: str, ts, cls: str, sheet, side: str, outcome: str, mark=None, detail=None) -> dict:
  return {"id": oid, "set": ts.document.alias, "split": ts.document.split.value.lower(), "class": cls, "sheet": sheet, "side": side, "outcome": outcome, "mark": mark, "detail": detail}

def _flagged(read_items: list, page=None, cls: str | None = None) -> bool:
  if page is not None and (page.coverage or {}).get(cls) in (V.Status.NOT_READ.value, V.Status.UNSURE.value):
    return True
  return any(i.status is not V.Status.READ for i in read_items)

def element_outcomes(key: str, ts: F.TruthSet, read: AD.SetRead) -> list:
  out, seen = [], {}
  by_scope: dict = {}
  for i, row in enumerate(ts.elements):
    by_scope.setdefault((row.sheet, row.cls.value), []).append(row)
  reads_by_scope: dict = {}
  for item in read.items:
    reads_by_scope.setdefault((item.sheet, item.cls.value), []).append(item)
  for (sheet, cls), truths in sorted(by_scope.items()):
    page = read.pages.get(sheet)
    reads = list(reads_by_scope.get((sheet, cls), []))
    used: set = set()
    
    marked = {}
    for t in truths:
      marked.setdefault(M.group_key(t.mark), []).append(t)
    order = [k for k in sorted(marked, key=lambda x: (x is None, x or ""))]
    
    for gk in order:
      group = marked[gk]
      pool = [j for j, r in enumerate(reads) if j not in used and (gk is None or M.group_key(r.mark) == gk)]
      counted = [t for t in group if isinstance((t.attrs or {}).get("count"), int) and t.attrs["count"] >= 2 and not t.geom]
      single = [t for t in group if t not in counted]
      for t in counted:
        total = sum(int(reads[j].attrs.get("count", 1)) for j in pool)
        n = seen[(sheet, cls, gk)] = seen.get((sheet, cls, gk), 0) + 1
        oid = f"{key}:EL:{sheet}:{cls}:{gk or '-'}:{n}"
        if not pool:
          verdict = MISSED_R if _flagged(reads, page, cls) else MISSED_S
        else:
          verdict = OK if M.counts_equal(t.attrs["count"], total) else WRONG
        out.append(_outcome(oid, ts, cls, sheet, "truth", verdict, t.mark, f"count truth {t.attrs['count']}, read {total}"))
        used.update(pool)
        pool = []
        
      pairs, left_t, _left_r = M.pair_group(single, [reads[j] for j in pool], page)
      matched = {li: pool[ri] for li, ri in pairs}
      for li, t in enumerate(single):
        n = seen[(sheet, cls, gk)] = seen.get((sheet, cls, gk), 0) + 1
        oid = f"{key}:EL:{sheet}:{cls}:{gk or '-'}:{n}"
        if li in matched:
          r = reads[matched[li]]
          used.add(matched[li])
          wrong, unread = M.compare_attrs(t.attrs, r.attrs)
          out.append(_outcome(oid, ts, cls, sheet, "truth", WRONG if wrong else OK, t.mark, ("wrong: " + ", ".join(wrong) if wrong else None) or ("not read: " + ", ".join(unread) if unread else None)))
        else:
          out.append(_outcome(oid, ts, cls, sheet, "truth", MISSED_R if _flagged(reads, page, cls) else MISSED_S, t.mark))
    for j, r in enumerate(reads):
      n = j + 1
      oid = f"{key}:RD:{sheet}:{cls}:{M.group_key(r.mark) or '-'}:{n}"
      if j in used:
        out.append(_outcome(oid, ts, cls, sheet, "read", TRUE, r.mark))
      else:
        out.append(_outcome(oid, ts, cls, sheet, "read", INV_S if r.status is V.Status.READ else INV_F, r.mark))
  return out

def register_outcomes(key: str, ts: F.TruthSet, read: AD.SetRead) -> list:
  out = []
  for row in ts.register:
    got = (read.pages.get(row.sheet).register if row.sheet in read.pages else {}) or {}
    for name in REGISTER_FIELDS:
      want = getattr(row, name)
      want = want.value if hasattr(want, "value") else want
      if want in (None, "UNKNOWN"):
        continue
      oid = f"{key}:REG:{row.sheet}:{name}"
      if row.sheet not in read.pages:
        out.append(_outcome(oid, ts, "REGISTER", row.sheet, "truth", MISSED_S, None, name))
      else:
        out.append(_outcome(oid, ts, "REGISTER", row.sheet, "truth", OK if M.field_equal(name, want, got.get(name)) else WRONG, None, f"{name}: truth {want}, read {got.get(name)}"))
  return out

def fact_outcomes(key: str, ts: F.TruthSet, facts: list, results: list, pdf: str) -> list:
  out, unjudged = [], 0
  for i, (f, r) in enumerate(zip(facts, results), 1):
    if (f.get("source") or {}).get("pdf") != pdf:
      continue
    verdict = FACT_OUTCOME.get(r.get("status"))
    if verdict is None:
      unjudged += 1
      continue
    out.append(_outcome(f"{key}:FACT:{i}", ts, V.ElementClass.NOTE_FACT.value, (f.get("source") or {}).get("page"), "truth", verdict, f.get("mark") or f.get("name"), f"{f.get('kind')}: {r.get('message')}"))
  return out

def param_completeness(ts: F.TruthSet) -> dict:
  counts = {s.value: 0 for s in V.ParamState}
  for p in ts.params:
    for spec in p.inputs.values():
      counts[spec["state"]] += 1
  total = sum(counts.values())
  return {"inputs": total, "states": counts, "complete": None if not total else round((counts["PRINTED"] + counts["DERIVED"]) / total, 4)}

def _case_facts(root: str, case: str) -> list:
  return CIO.load_facts(os.path.join(root, case, "facts.yaml"))

def run(split: str, cases_dir: str | None, score_dir: str | None = None, root: str = CIO.HERE) -> dict:
  want = {"dev": ("DEV",), "heldout": ("HELDOUT",), "all": ("DEV", "HELDOUT")}[split]
  files_dir = CIO.cases_dir(cases_dir)
  outcomes, sets_out, unmapped, notes = [], [], {}, []
  reads_by_case: dict = {}
  for ref in S.find_sets(cases_dir, root):
    if ref.link:
      continue
    ts = F.load_set(ref.truth_folder)
    if ts.document.split.value not in want:
      continue
  
    facts = [f for f in _case_facts(root, ref.case) if (f.get("source") or {}).get("pdf") == ref.pdf]
    needs_read = bool(ts.elements or ts.register)
    results_all = None
    if facts:
      doc_path = os.path.join(score_dir, ref.case, "score.json") if score_dir else None
      if doc_path and os.path.isfile(doc_path):
        with open(doc_path, encoding="utf-8") as fh:
          results_all = json.load(fh).get("facts") or []
      else:
        needs_read = True
    read = AD.SetRead()
    
    if needs_read:
      case = CIO.load_case(os.path.join(root, ref.case))
      found, problems = CIO.find_files(case, files_dir)
      if problems:
        raise RuntimeError("; ".join(problems))
      if ref.case not in reads_by_case:
        reads_by_case[ref.case] = AD.read_case(case, found)
      rows = reads_by_case[ref.case]
      read = AD.items_of(rows[ref.pdf])
      for k, n in read.unmapped.items():
        unmapped[k] = unmapped.get(k, 0) + n
      if facts and results_all is None:
        from app.modules.drawings_boq.takeoff.proof import score as SC
        results_all = SC.check_facts([r for rs in rows.values() for r in rs], case["facts"])
        
    case_facts = _case_facts(root, ref.case)
    out = element_outcomes(ref.pdf_key, ts, read) + register_outcomes(ref.pdf_key, ts, read)
    if facts:
      out += fact_outcomes(ref.pdf_key, ts, case_facts, results_all, ref.pdf)
      
    outcomes += out
    sets_out.append({"alias": ts.document.alias, "key": ref.pdf_key, "split": ts.document.split.value.lower(), "pages": ts.document.pages, "consultant": ts.document.consultant, "producer": ts.document.producer, "outcomes": len(out), "params": param_completeness(ts)})
  digest = hashlib.sha256("\n".join(sorted(f"{o['id']}|{o['outcome']}" for o in outcomes)).encode()).hexdigest()
  return {"split": split, "hash": digest, "truth_fingerprint": truth_fingerprint(root), "sets": sets_out, "outcomes": outcomes, "unmapped": dict(sorted(unmapped.items())), "metrics": metrics(outcomes, sets_out), "notes": notes}

def _tally(rows: list) -> dict:
  c = {k: 0 for k in (*TRUTH_SIDE, TRUE, INV_S, INV_F)}
  for o in rows:
    c[o["outcome"]] += 1
  truth = c[OK] + c[WRONG] + c[MISSED_S] + c[MISSED_R]
  judged = c[TRUE] + c[INV_S] + c[INV_F]
  matched = c[OK] + c[WRONG]
  silent = c[WRONG] + c[INV_S]
  unread = c[MISSED_S] + c[MISSED_R]
  
  return {**c, "truth": truth, "matched": matched, "judged_reads": judged, "silent_wrong": silent,
    "recall": None if not truth else round(matched / truth, 4), "recall_ci": wilson(matched, truth),
    "value_accuracy": None if not matched else round(c[OK] / matched, 4), "value_accuracy_ci": wilson(c[OK], matched),
    "precision": None if not judged else round(c[TRUE] / judged, 4), "precision_ci": wilson(c[TRUE], judged),
    "silent_wrong_rate": None if not judged else round(silent / judged, 4), "silent_wrong_rate_ci": wilson(silent, judged),
    "honest_unread": None if not unread else round(c[MISSED_R] / unread, 4), "honest_unread_ci": wilson(c[MISSED_R], unread)}

def metrics(outcomes: list, sets_out: list) -> dict:
  styles = {s["alias"]: s for s in sets_out}
  out = {"by_split_class": {}, "by_set": {}, "by_style": {}}
  groups: dict = {}
  
  for o in outcomes:
    s = styles.get(o["set"], {})
    for name, key in (("by_split_class", f"{o['split']}|{o['class']}"), ("by_set", f"{o['set']}|{o['class']}"),
      ("by_style", f"consultant={s.get('consultant') or 'unknown'}"), ("by_style", f"producer={s.get('producer') or 'unknown'}")):
      groups.setdefault((name, key), []).append(o)
  for (name, key), rows in sorted(groups.items()):
    out[name][key] = _tally(rows)
  out["by_split"] = {sp: _tally([o for o in outcomes if o["split"] == sp]) for sp in sorted({o["split"] for o in outcomes})}
  return out

def silent_count(outcomes: list) -> dict:
  per: dict = {}
  for o in outcomes:
    if o["outcome"] in (MISSED_S, INV_S):
      per[o["split"]] = per.get(o["split"], 0) + 1
  return per

def to_baseline(doc: dict) -> dict:
  return {"hash": doc["hash"], "truth_fingerprint": doc["truth_fingerprint"], "outcomes": {o["id"]: o["outcome"] for o in doc["outcomes"]},
    "splits": {o["id"]: o["split"] for o in doc["outcomes"]}, "silent": silent_count(doc["outcomes"])}

def load_baseline(path: str = BASELINE) -> dict | None:
  if not os.path.isfile(path):
    return None
  with open(path, encoding="utf-8") as fh:
    return json.load(fh)

def load_accepted(path: str = ACCEPTED) -> dict:
  if not os.path.isfile(path):
    return {}
  with open(path, encoding="utf-8") as fh:
    rows = yaml.safe_load(fh) or []
  return {str(r["id"]): str(r.get("reason") or "") for r in rows if isinstance(r, dict) and r.get("id") and r.get("reason")}

def compare(baseline: dict, doc: dict, accepted: dict) -> dict:
  now = {o["id"]: o["outcome"] for o in doc["outcomes"]}
  splits = {o["id"]: o["split"] for o in doc["outcomes"]}
  lost = [i for i, was in sorted(baseline["outcomes"].items()) if was == OK and i in now and now[i] != OK and i not in accepted]
  gone = [i for i, was in sorted(baseline["outcomes"].items()) if was == OK and i not in now and i not in accepted]
  reg_down = [i for i in lost if ":REG:" in i]
  same_truth = baseline.get("truth_fingerprint") == doc["truth_fingerprint"]
  common = set(baseline["outcomes"]) & set(now)
  before: dict = {}
  after: dict = {}
  
  for i in common:
    if baseline["outcomes"][i] == MISSED_S:
      before[baseline["splits"][i]] = before.get(baseline["splits"][i], 0) + 1
    if now[i] == MISSED_S:
      after[splits[i]] = after.get(splits[i], 0) + 1
      
  if same_truth:
    for i, o in baseline["outcomes"].items():
      if o == INV_S:
        before[baseline["splits"][i]] = before.get(baseline["splits"][i], 0) + 1
    for i, o in now.items():
      if o == INV_S:
        after[splits[i]] = after.get(splits[i], 0) + 1
  rises = {sp: (before.get(sp, 0), after[sp]) for sp in sorted(after) if after[sp] > before.get(sp, 0)}
  changed = [(i, baseline["outcomes"][i], now[i]) for i in sorted(common) if baseline["outcomes"][i] != now[i]]
  return {"lost": lost, "gone": gone, "register_down": reg_down, "silent_rises": rises, "same_truth": same_truth, "changed": changed, "ok": not lost and not gone and not rises}

def gate(cases_dir: str | None, score_dir: str | None, root: str = CIO.HERE) -> tuple:
  baseline = load_baseline()
  if baseline is None:
    return False, "proof/reading/baseline.json is missing (write it with `proof.reading score --split all --write-baseline` once the reading is right)"
  doc = run("all", cases_dir, score_dir, root)
  cmp = compare(baseline, doc, load_accepted())
  if cmp["ok"]:
    n_ok = sum(1 for v in baseline["outcomes"].values() if v == OK)
    return True, f"{n_ok} truth item(s) still MATCHED_OK; silent-wrong not up" + ("" if cmp["same_truth"] else "; the truth changed since the baseline was written")

  bad = []
  if cmp["lost"]:
    bad.append(f"{len(cmp['lost'])} truth item(s) no longer MATCHED_OK: " + ", ".join(cmp["lost"][:6]) + (" ..." if len(cmp["lost"]) > 6 else ""))
  if cmp["gone"]:
    bad.append(f"{len(cmp['gone'])} truth item(s) are no longer in the truth: " + ", ".join(cmp["gone"][:6]))
  if cmp["register_down"]:
    bad.append(f"{len(cmp['register_down'])} register field(s) went from right to wrong")
  for sp, (b, a) in cmp["silent_rises"].items():
    bad.append(f"silent misses and inventions rose on {sp}: {b} to {a}")
  return False, "; ".join(bad)
