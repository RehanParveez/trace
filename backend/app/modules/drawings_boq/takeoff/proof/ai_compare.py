"""Prompt competition and the example bank, scored from the cached answers (no model is called). A prompt version, or the same version with and without examples, is a variant: 1, 2, 2+ex (examples shown) or 2+ex-loo (examples shown, none from the office read). proof.ai_eval --compare A B scores two variants on the pages both answered, office by office, and says whether B may replace A: it must help two offices and hurt none. --loo shows each office's score without examples, with them, and with them minus its own office's, which is the gain on a firm the bank has never seen. --build-examples fills the bank from answers a person has checked."""
from __future__ import annotations
import os
from app.modules.drawings_boq.takeoff.ai_reader import cache as CACHE
from app.modules.drawings_boq.takeoff.ai_reader import examples as EX
from app.modules.drawings_boq.takeoff.ai_reader import schedule as SCH
from app.modules.drawings_boq.takeoff.proof import ai_eval as AE
from app.modules.drawings_boq.takeoff.proof import case_io as CIO
from app.modules.drawings_boq.takeoff.proof.reading import formats as F
from app.modules.drawings_boq.takeoff.proof.reading import sets as S
from app.modules.drawings_boq.takeoff.proof.reading.formats import KEY_LEN

TASK = SCH.TASK
MIN_TRUTH = 10
LOO = EX.LEAVE_OUT

def variant_of(entry: dict) -> str:
  return str(entry.get("variant") or entry.get("prompt_version") or "")

def page_score(entry: dict, truth: list) -> dict:
  """What one cached answer is worth on its page: the rows it accepted and judged (a row of a kind the page's truth has rows for), how many of those are a truth row, how many truth rows the page has, and how many were read by an accepted row."""
  judged = right = 0
  read: set = set()
  for sched in (entry.get("answer") or {}).get("schedules") or []:
    cls = AE.SCHEDULE_CLASSES.get(sched["kind"])
    rows_truth = [t for t in truth if t.cls.value == cls]
    for row in sched["rows"]:
      if not rows_truth:
        continue
      judged += 1
      hit = [t for t in rows_truth if AE._row_matches(sched["kind"], row, t)]
      right += 1 if hit else 0
      read.update(id(t) for t in hit)
  wanted = [t for t in truth if t.cls.value in AE.SCHEDULE_CLASSES.values()]
  return {"judged": judged, "right": right, "truth": len(wanted), "read": len(read), "checked": sum(1 for t in wanted if t.truth is not None and t.truth.checked is True)}

def collect(cases_dir: str | None = None, root: str = CIO.HERE) -> dict:
  """{(office, variant): {(pdf key, page): score + own_fed}} over every cached SCHEDULE_ROW answer that is OK. own_fed is True when an example from the page's own office was shown."""
  refs: dict = {}
  for ref in S.find_sets(cases_dir, root):
    refs.setdefault(ref.pdf_key, ref)
  bank = {e.id: e for e in EX.load_all(root, CIO.list_cases(root, audit=True))}
  truth_of: dict = {}
  out: dict = {}
  for name in CIO.list_cases(root, audit=True):
    for e in CACHE.read_all(os.path.join(root, name)):
      if e.get("task") != TASK or e.get("status") != "OK":
        continue
      key = str(e["pdf_sha256"])[:KEY_LEN]
      ref = refs.get(key)
      if ref is None:
        continue
      if key not in truth_of:
        truth_of[key] = F.load_set(ref.truth_folder).elements
      truth = [t for t in truth_of[key] if t.sheet == int(e["page"])]
      score = page_score(e, truth)
      ids = (e.get("examples") or {}).get("ids") or []
      score["own_fed"] = any(bank[i].office == ref.office for i in ids if i in bank)
      out.setdefault((ref.office, variant_of(e)), {})[(key, int(e["page"]))] = score
  return out

def totals(pages: dict, keys) -> dict:
  t = {"judged": 0, "right": 0, "truth": 0, "read": 0, "checked": 0, "pages": 0}
  for k in keys:
    s = pages[k]
    t["pages"] += 1
    for f in ("judged", "right", "truth", "read", "checked"):
      t[f] += s[f]
  t["precision"] = t["right"] / t["judged"] if t["judged"] else None
  t["recall"] = t["read"] / t["truth"] if t["truth"] else None
  return t

def verdict(a: dict, b: dict) -> str:
  """helped, hurt, same or too_little for one office, B against A on the same pages. Recall up with precision not down is a help; recall down or precision down is a hurt; with fewer than MIN_TRUTH truth rows there is too little to say."""
  if a["truth"] < MIN_TRUTH:
    return "too_little"
  lower_p = a["precision"] is not None and b["precision"] is not None and b["precision"] < a["precision"]
  if b["recall"] < a["recall"] or lower_p:
    return "hurt"
  if b["recall"] > a["recall"]:
    return "helped"
  return "same"

def compare(data: dict, a: str, b: str) -> dict:
  """B against A, office by office, on the pages both variants answered. When B shows examples, a page that was shown an example of its own office does not count towards the verdict (that gain belongs to the office the examples came from, not to a firm Trace has never seen); it is listed apart."""
  offices = sorted({o for (o, v) in data if v == a} & {o for (o, v) in data if v == b})
  rows = []
  for o in offices:
    pa, pb = data[(o, a)], data[(o, b)]
    common = set(pa) & set(pb)
    general = {k for k in common if not pb[k]["own_fed"]}
    ta, tb = totals(pa, general), totals(pb, general)
    rows.append({"office": o, "pages": len(common), "own_fed": len(common) - len(general), "a": ta, "b": tb, "verdict": verdict(ta, tb) if general else "too_little"})
  helped = [r["office"] for r in rows if r["verdict"] == "helped"]
  hurt = [r["office"] for r in rows if r["verdict"] == "hurt"]
  return {"a": a, "b": b, "offices": rows, "helped": helped, "hurt": hurt, "replaces": len(helped) >= 2 and not hurt}

def loo(data: dict, base: str) -> list:
  """For each office the score of the base prompt without examples, with examples, and with examples minus its own office's, on the pages all three answered."""
  with_ex, without_own = f"{base}+ex", f"{base}+ex{LOO}"
  rows = []
  for o in sorted({o for (o, v) in data}):
    have = [v for v in (base, with_ex, without_own) if (o, v) in data]
    keys = set.intersection(*[set(data[(o, v)]) for v in have]) if have else set()
    rows.append({"office": o, "pages": len(keys), **{v: totals(data[(o, v)], keys) for v in have}})
  return rows

def pct(x) -> str:
  return "none" if x is None else f"{100.0 * x:.1f}%"

def lines_compare(r: dict) -> list:
  out = [f"{r['b']} against {r['a']} (SCHEDULE_ROW, the pages both answered):"]
  for o in r["offices"]:
    a, b = o["a"], o["b"]
    out.append(f"  office {o['office']}: {o['pages']} page(s), {o['own_fed']} left out for an example of its own office; recall {pct(a['recall'])} to {pct(b['recall'])} ({b['read']} of {b['truth']} truth rows), "
      f"precision {pct(a['precision'])} to {pct(b['precision'])} ({b['right']} of {b['judged']} judged rows): {o['verdict'].upper()}")
  out.append("  " + (f"{r['b']} helps {', '.join(r['helped'])} and hurts none: it may replace {r['a']}. Record it in docs/packs/generality.yaml." if r["replaces"] else
    f"{r['b']} does not replace {r['a']}: it helps {len(r['helped'])} office(s) ({', '.join(r['helped']) or 'none'}) and hurts {len(r['hurt'])} ({', '.join(r['hurt']) or 'none'}); two helped and none hurt are needed."))
  if not r["offices"]:
    out.append("  No office has answers of both variants on the same page: fill the cache for both (proof/ai_cache, ai_reader.fill_cache) and run again.")
  return out

def lines_loo(rows: list, base: str) -> list:
  out = [f"Each office's SCHEDULE_ROW score, prompt {base} without examples, with examples, and with examples minus its own office's (the pages all three answered):"]
  for r in rows:
    cells = []
    for v in (base, f"{base}+ex", f"{base}+ex{LOO}"):
      t = r.get(v)
      cells.append(f"{v}: " + ("not answered" if t is None else f"recall {pct(t['recall'])}, precision {pct(t['precision'])}"))
    first = r.get(f"{base}+ex{LOO}")
    out.append(f"  office {r['office']} ({r['pages']} page(s)): " + "; ".join(cells))
    if first is None or r.get(base) is None:
      out.append("    no gain on an unseen firm can be said for this office yet: it lacks the answers of one of the variants.")
  return out

def build_examples(cases_dir: str | None = None, root: str = CIO.HERE, write: bool = False) -> dict:
  """Makes examples from the cached answers a person has checked: an accepted row that is a truth row whose truth was checked (checked: true with a checked_by) is kept, with the words of its quote, its office, its kind and the page it stands on. Counts what it would keep; writes the files into <case>/ai_examples only with write."""
  refs: dict = {}
  for ref in S.find_sets(cases_dir, root):
    refs.setdefault(ref.pdf_key, ref)
  made: dict = {}
  skipped = {"unchecked": 0, "no_truth": 0}
  truth_of: dict = {}
  for name in CIO.list_cases(root, audit=True):
    for e in CACHE.read_all(os.path.join(root, name)):
      if e.get("task") != TASK or e.get("status") != "OK":
        continue
      key = str(e["pdf_sha256"])[:KEY_LEN]
      ref = refs.get(key)
      if ref is None:
        continue
      if key not in truth_of:
        truth_of[key] = F.load_set(ref.truth_folder).elements
      truth = [t for t in truth_of[key] if t.sheet == int(e["page"])]
      for sched in (e.get("answer") or {}).get("schedules") or []:
        cls = AE.SCHEDULE_CLASSES.get(sched["kind"])
        for row in sched["rows"]:
          hit = [t for t in truth if t.cls.value == cls and AE._row_matches(sched["kind"], row, t)]
          if not hit:
            skipped["no_truth"] += 1
            continue
          stamp = hit[0].truth
          if stamp is None or stamp.checked is not True or not str(stamp.checked_by or "").strip():
            skipped["unchecked"] += 1
            continue
          ex = EX.make(task=TASK, office=ref.office if ref.office != S.UNKNOWN_OFFICE else None, kind=sched["kind"], crop_ref={"pdf_sha256": e["pdf_sha256"], "page": int(e["page"]), "region": e.get("region")},
            text=row.get("quote"), answer={"kind": sched["kind"], **row}, checked_by=stamp.checked_by, date=stamp.checked_date or stamp.date, drawing=str(e["pdf_sha256"]))
          made[ex.id] = (ref.owner, ex)
  if write:
    for owner, ex in made.values():
      EX.save(os.path.join(root, owner), ex)
  return {"examples": len(made), "by_office": {o: sum(1 for _w, x in made.values() if (x.office or "?") == o) for o in sorted({(x.office or "?") for _w, x in made.values()})}, "skipped": skipped, "written": write}
