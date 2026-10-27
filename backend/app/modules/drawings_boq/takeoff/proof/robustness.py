from __future__ import annotations
import argparse
import io
import json
import os
import sys
import time

from app.modules.drawings_boq.takeoff.proof import perturb as PB
from app.modules.drawings_boq.takeoff.proof import readsummary as RS

def scan_copy(pdf: bytes, dpi: int = 150, skew_deg: float = 0.6, noise: float = 0.01, seed: int = 1) -> bytes:
  import numpy as np
  import pypdfium2 as pdfium
  from PIL import Image
  rng = np.random.default_rng(seed)
  doc = pdfium.PdfDocument(pdf)
  pages = []

  for i in range(len(doc)):
    img = doc[i].render(scale=dpi / 72.0).to_pil().convert("L")
    if skew_deg:
      img = img.rotate(skew_deg, resample=Image.BICUBIC, expand=True, fillcolor=255)
    a = np.asarray(img).copy()
    if noise:
      m = rng.random(a.shape)
      a[m < noise / 2] = 0
      a[m > 1 - noise / 2] = 255
    pages.append(Image.fromarray(((a > 160) * 255).astype("uint8")).convert("1"))

  buf = io.BytesIO()
  pages[0].save(buf, "PDF", resolution=float(dpi), save_all=True, append_images=pages[1:])
  return buf.getvalue()

SCANS = (
  ("scan 150 dpi, skew 0.6", lambda p: scan_copy(p, 150, 0.6)),
  ("scan 200 dpi, skew 0.6", lambda p: scan_copy(p, 200, 0.6)),
  ("scan 150 dpi, skew 2.0, noisy", lambda p: scan_copy(p, 150, 2.0, 0.03)),
  ("scan 200 dpi, skew 4.0", lambda p: scan_copy(p, 200, 4.0, 0.01)),
)

SUITES = {
  "quick": tuple(s for s in PB.SUITE if s[0] in ("rotate view 90", "turn drawing 90", "enlarge to double size", "shrink to half size", "drop the title block", "strip all text")) + SCANS[:1],
  "full": tuple(PB.SUITE) + SCANS,
  "angled": tuple(PB.SUITE_ANGLED),
  "scan": SCANS,
}

EMPTY = {"counts": {}, "rooms": {}, "slab_m2": {}, "wall_m": {}}

def words_of(pdf: bytes, pages: list | None = None, budget_s: float = 75.0) -> dict:
  """{page: [WORDS]} as the reader gets them, with the picture reading used on a scanned or line-lettered page. Words of two letters or more with a letter or digit in them."""
  from app.modules.drawings_boq.takeoff.prep.extract import extract_page, open_document
  doc = open_document(pdf)
  out: dict = {}

  for i in range(len(doc)):
    if pages and (i + 1) not in pages:
      continue
    try:
      raw = extract_page(doc, i, budget_s=budget_s)
      out[i + 1] = [w.text.upper() for w in raw.words if len(w.text) >= 2 and any(ch.isalnum() for ch in w.text)]
    except Exception:
      out[i + 1] = []
  return out

def text_score(clean: dict, new: dict) -> dict:
  """Share of the clean words found again (recall) and share of the damaged read's words that are in the clean read (precision), pooled over the pages."""
  from collections import Counter
  tot = got = kept = 0
  per: dict = {}

  for p, a in clean.items():
    ca, cb = Counter(a), Counter(new.get(p) or [])
    m = sum((ca & cb).values())
    tot, got, kept = tot + len(a), got + sum(cb.values()), kept + m
    per[p] = {"clean": len(a), "found": sum(cb.values()), "kept": m}
  return {"clean_words": tot, "found_words": got, "recall": round(kept / tot, 3) if tot else None, "precision": round(kept / got, 3) if got else None, "pages": per}

def _close(a, b, tol) -> bool:
  return a is not None and b is not None and abs(a - b) <= tol * max(abs(a), abs(b), 1e-9)

def _page_score(b: dict, n: dict) -> dict:
  out: dict = {}

  for cat in set(b["counts"]) | set(n["counts"]):
    base = kept = extra = 0
    fb, fn = b["counts"].get(cat, {}), n["counts"].get(cat, {})
    for fl in set(fb) | set(fn):
      for tag in set(fb.get(fl, {})) | set(fn.get(fl, {})):
        x, y = fb.get(fl, {}).get(tag, 0), fn.get(fl, {}).get(tag, 0)
        base, kept, extra = base + x, kept + min(x, y), extra + max(y - x, 0)
    out[cat] = [base, kept, extra]
  rb = ra = re_ = 0

  for fl in set(b["rooms"]) | set(n["rooms"]):
    x, y = b["rooms"].get(fl, {}), n["rooms"].get(fl, {})
    rb += len(x)
    ra += sum(1 for k in x if _close(x[k], y.get(k), 0.03))
    re_ += sum(1 for k in y if k not in x)
  if rb or re_:
    out["ROOM_AREA"] = [rb, ra, re_]
  for key, tol, name in (("wall_m", 0.02, "WALL_LENGTH"), ("slab_m2", 0.03, "SLAB_AREA")):
    x, y = b[key], n[key]
    if x or y:
      out[name] = [len(x), sum(1 for k in x if _close(x[k], y.get(k), tol)), sum(1 for k in y if k not in x)]
  return out

def score(base_read: list, new_read: list) -> dict:
  b, n = RS.pages(base_read), RS.pages(new_read)
  bn = {sh["page_no"]: set(sh.get("notes") or []) for sh in base_read}
  nn = {sh["page_no"]: set(sh.get("notes") or []) for sh in new_read}
  fam: dict = {}

  changed, silent, unread = [], [], []
  for p in sorted(b):
    if p not in n:
      unread.append(p)
      if RS.compare(b[p], EMPTY):
        changed.append(p)
      for k, v in _page_score(b[p], EMPTY).items():
        t = fam.setdefault(k, [0, 0, 0])
        t[0] += v[0]
      continue
    for k, v in _page_score(b[p], n[p]).items():
      t = fam.setdefault(k, [0, 0, 0])
      for i in range(3):
        t[i] += v[i]
    if RS.compare(b[p], n[p]):
      changed.append(p)
      if not (nn.get(p, set()) - bn.get(p, set())):
        silent.append(p)
  return {"families": {k: {"base": v[0], "kept": v[1], "extra": v[2], "recall": round(v[1] / v[0], 3) if v[0] else None} for k, v in sorted(fam.items())},
    "pages": len(b), "pages_changed": changed, "pages_silent": silent, "pages_unread": unread}

def run(pdf: bytes, suite: tuple, pages: list | None = None, log=print, text: bool = False) -> dict:
  from app.modules.drawings_boq.takeoff.proof.benchmark import read_pdf
  t0 = time.monotonic()
  base, base_problems = read_pdf(pdf, pages)
  clean_words = words_of(pdf, pages) if text else None
  log(f"clean read: {len(base)} pages in {time.monotonic() - t0:.0f}s")
  out = {"clean": {"pages": len(base), "problems": base_problems, "totals": RS.summary(base)["totals"]}, "variants": {}}

  for name, fn in suite:
    t = time.monotonic()
    try:
      damaged = fn(pdf)
      new, problems = read_pdf(damaged, pages)
    except Exception as exc:

      out["variants"][name] = {"error": f"{type(exc).__name__}: {str(exc)[:120]}"}
      log(f"{name}: failed ({type(exc).__name__})")
      continue
    s = score(base, new)
    s["problems"] = problems
    if text:
      s["text"] = text_score(clean_words, words_of(damaged, pages))
    s["seconds"] = round(time.monotonic() - t, 1)
    out["variants"][name] = s
    log(f"{name}: {len(s['pages_changed'])} of {s['pages']} pages changed, {len(s['pages_silent'])} silently ({s['seconds']}s)")
  return out

def render(name: str, rep: dict) -> str:
  fams = sorted({f for v in rep["variants"].values() if "families" in v for f in v["families"]})
  fams = [f for f in fams if any(v["families"].get(f, {}).get("base") for v in rep["variants"].values() if "families" in v)]
  W = max([len(f) for f in fams] + [6]) + 2
  head = f"{name}: clean read {rep['clean']['pages']} pages, totals {rep['clean']['totals']}\n"
  has_text = any("text" in v for v in rep["variants"].values())
  rows = ["variant".ljust(32) + "".join(f.rjust(W) for f in fams) + "  changed  silent" + ("  words_recall  words_precision" if has_text else "")]
  for vn, v in rep["variants"].items():
    if "error" in v:
      rows.append(vn.ljust(32) + "  " + v["error"])
      continue
    cells = []
    for f in fams:
      x = v["families"].get(f)
      cells.append((f"{x['recall']:.2f}" + ("+" if x["extra"] else " ") if x and x["recall"] is not None else "-").rjust(W))
    tx = ""
    if has_text:
      t = v.get("text") or {}
      tx = f"{t.get('recall', '-'):>14}{t.get('precision', '-'):>17}"
    rows.append(vn.ljust(32) + "".join(cells) + f"{len(v['pages_changed']):>9}{len(v['pages_silent']):>8}" + tx)
  return head + "\n".join(rows) + "\n(recall = share of the clean read still read the same; + = the damaged read also has items the clean read did not)\n"

def compare_baseline(rep: dict, base: dict, slack: float = 0.02) -> list:
  out = []
  for vn, v in rep["variants"].items():
    b = (base.get("variants") or {}).get(vn)
    if not b or "families" not in v or "families" not in b:
      continue
    for f, x in v["families"].items():
      y = b["families"].get(f)
      if y and x["recall"] is not None and y["recall"] is not None and x["recall"] < y["recall"] - slack:
        out.append({"variant": vn, "family": f, "was": y["recall"], "now": x["recall"]})
    if len(v["pages_silent"]) > len(b.get("pages_silent") or []):
      out.append({"variant": vn, "family": "SILENT_PAGES", "was": len(b.get("pages_silent") or []), "now": len(v["pages_silent"])})
  return out

def main(argv: list | None = None) -> int:
  ap = argparse.ArgumentParser(description="Read a set clean and damaged, and count what survives.")
  ap.add_argument("pdf")
  ap.add_argument("--suite", default="quick", choices=sorted(SUITES))
  ap.add_argument("--pages")
  ap.add_argument("--text", action="store_true", help="also count the words read, clean and damaged (slow on scans: each is read from its picture)")
  ap.add_argument("--json")
  ap.add_argument("--save-baseline")
  ap.add_argument("--baseline")
  a = ap.parse_args(argv)

  pages = [int(p) for p in a.pages.split(",")] if a.pages else None
  rep = run(open(a.pdf, "rb").read(), SUITES[a.suite], pages, text=a.text)
  print("\n" + render(os.path.basename(a.pdf), rep))
  rc = 0
  if a.baseline and os.path.exists(a.baseline):
    worse = compare_baseline(rep, json.load(open(a.baseline, encoding="utf-8")))
    for w in worse:
      print(f"WORSE {w['variant']} / {w['family']}: {w['was']} -> {w['now']}")
    rc = 1 if worse else 0
  if a.json:
    json.dump(rep, open(a.json, "w", encoding="utf-8"), indent=1, default=str)
  if a.save_baseline:
    json.dump(rep, open(a.save_baseline, "w", encoding="utf-8"), indent=1, default=str)
  return rc

if __name__ == "__main__":
  sys.exit(main())
