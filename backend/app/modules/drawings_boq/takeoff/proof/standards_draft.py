from __future__ import annotations
import datetime
import json
import os
import re
import sys
import urllib.parse
import yaml
from app.core.config import settings
from app.engine.catalogue import conventions as CV
from app.engine.catalogue import standards as ST
from app.modules.ai_requests import cap as CAP
from app.modules.drawings_boq.takeoff.ai_reader import cache as CACHE
from app.modules.drawings_boq.takeoff.ai_reader import cost as COST
from app.modules.drawings_boq.takeoff.proof import case_io as CIO

HERE = os.path.dirname(os.path.abspath(__file__))
DRAFTS = os.path.join(HERE, "standards_drafts")
AI_CASE = os.path.join(DRAFTS, "_ai")
CARDS = os.path.join(HERE, "standards_draft_cards.yaml")
TASK, PROMPT_VERSION = "STANDARD_DRAFT", "v1"
TOOL_TYPE, TOOL_NAME = "web_search_20250305", "web_search"
SEARCH_USD = 0.01
MAX_USES, MAX_TOKENS, MAX_PAUSES = 5, 2000, 3
CHECKED, FAILED, NOT_FOUND, UNPARSED = "CHECKED", "FAILED_CHECKS", "NOT_FOUND", "UNPARSED"
CODE_HOSTS = ("pec.org.pk", "concrete.org", "astm.org", "iso.org", "bsigroup.com", "aci-int.org", "icc-es.org", "bis.gov.in")
TWO_LEVEL = {"gov.pk", "com.pk", "org.pk", "edu.pk", "net.pk", "co.uk", "org.uk", "gov.uk", "ac.uk", "com.au", "gov.au", "gov.in", "co.in", "gov.bd", "com.bd"}
ALIASES = {"%": "percent", "per cent": "percent", "percentage": "percent", "mm²": "mm2", "sq mm": "mm2", "m/point": "m_per_point", "m per point": "m_per_point", "metres per point": "m_per_point",
  "meters per point": "m_per_point", "points/room": "points_per_room", "points per room": "points_per_room", "metre": "m", "metres": "m", "meter": "m", "meters": "m", "inch": "in", "inches": "in"}
FRACTIONS = {"½": 0.5, "¼": 0.25, "¾": 0.75, "⅓": 1 / 3, "⅔": 2 / 3, "⅛": 0.125}
NUMBER = re.compile(r"(?<![\w.])(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d+))?(?:\s*([½¼¾⅓⅔⅛])|\s+(\d+)\s*/\s*(\d+))?|([½¼¾⅓⅔⅛])|(?<![\w.])(\d+)\s*/\s*(\d+)(?![\w.])")

def today() -> str:
  return datetime.date.today().isoformat()

def cards(path: str = CARDS) -> list:
  with open(path, encoding="utf-8") as fh:
    return (yaml.safe_load(fh) or {}).get("cards") or []

def card_of(card_id: str) -> dict | None:
  for c in cards():
    if c["id"] == card_id:
      return c
  return None

def units() -> list:
  return [u for u in ST.UNITS if u != "table"]

def unit_of(text) -> str | None:
  t = re.sub(r"\s+", " ", str(text or "").strip().lower())
  t = ALIASES.get(t, t)
  return t if t in units() else None

def numbers_in(text: str) -> list:
  out = []
  for m in NUMBER.finditer(str(text or "")):
    whole, dec, glyph, num, den, lone, a, b = m.groups()
    if lone:
      out.append(FRACTIONS[lone])
    elif a:
      out.append(float(a) / float(b) if float(b) else float("nan"))
    else:
      v = float(whole.replace(",", "") + ("." + dec if dec else ""))
      if glyph:
        v += FRACTIONS[glyph]
      elif num and float(den):
        v += float(num) / float(den)
      out.append(v)
  return [v for v in out if v == v]

def has_number(text: str, value) -> bool:
  want = float(value)
  return any(abs(n - want) <= 1e-9 * max(1.0, abs(want)) for n in numbers_in(text))

def domain_of(url: str) -> str:
  host = (urllib.parse.urlparse(str(url or "")).hostname or "").lower()
  host = host[4:] if host.startswith("www.") else host
  parts = host.split(".")
  if len(parts) >= 3 and ".".join(parts[-2:]) in TWO_LEVEL:
    return ".".join(parts[-3:])
  return ".".join(parts[-2:]) if len(parts) >= 2 else host

def canon(url: str) -> str:
  u = urllib.parse.urlparse(str(url or "").strip())
  host = (u.hostname or "").lower()
  return (host[4:] if host.startswith("www.") else host) + u.path.rstrip("/")

def rank_of(url: str) -> int:
  d = domain_of(url)
  if d.endswith("punjab.gov.pk"):
    return 0
  if any(d == h or d.endswith("." + h) for h in CODE_HOSTS):
    return 1
  labels = d.split(".")
  if "gov" in labels or "gob" in labels:
    return 2
  if "edu" in labels or "ac" in labels:
    return 3
  return 4

def prompt_for(card: dict, question: str) -> str:
  return (f"You research one figure for a Pakistani quantity surveyor's standards library. Card: {card['id']}. Question: {question}\n\n"
    "Use web search. Prefer, in this order: the Punjab Market Rate System (MRS) book and its specifications; the Building Code of Pakistan and the codes it adopts (ACI 318, ASTM, BS); "
    "other provinces' official schedules and CPWD; then manufacturers. Never rely on a blog alone.\n\n"
    "Reply with one JSON object and nothing else:\n"
    '{"value": <number or null>, "unit": "<one of: ' + ", ".join(units()) + '>", "range": [low, high] or null, '
    '"sources": [{"url": "...", "title": "...", "quote": "<the exact words on the page that contain the number>"}], "notes": "<where sources disagree, in one or two sentences>"}\n\n'
    "Give at least two sources from different websites. Copy each quote from the page; it must contain the number you give. If you cannot find the figure, give \"value\": null and say in notes what you searched. Do not guess.")

def request_body(card: dict, question: str, model: str, max_tokens: int, max_uses: int) -> dict:
  return {"model": model, "max_tokens": int(max_tokens), "messages": [{"role": "user", "content": prompt_for(card, question)}],
    "tools": [{"type": TOOL_TYPE, "name": TOOL_NAME, "max_uses": int(max_uses)}]}

def ask_api(card: dict, question: str, model: str, max_tokens: int = MAX_TOKENS, max_uses: int = MAX_USES, timeout_s: float = 180.0) -> dict:
  import httpx
  if not settings.ai_api_key:
    raise RuntimeError("AI_API_KEY is not set.")
  body = request_body(card, question, model, max_tokens, max_uses)
  got = {"text": "", "seen": [], "cited": [], "input_tokens": 0, "output_tokens": 0, "searches": 0, "stop_reason": None}
  for _ in range(MAX_PAUSES + 1):
    resp = httpx.post(settings.ai_anthropic_url, headers={"x-api-key": settings.ai_api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"}, json=body, timeout=timeout_s)
    resp.raise_for_status()
    doc = resp.json()
    use = doc.get("usage") or {}
    
    got["input_tokens"] += int(use.get("input_tokens") or 0)
    got["output_tokens"] += int(use.get("output_tokens") or 0)
    got["searches"] += int(((use.get("server_tool_use") or {}).get("web_search_requests")) or 0)
    got["stop_reason"] = doc.get("stop_reason")
    for block in doc.get("content") or []:
      kind = block.get("type")
      if kind == "text":
        got["text"] += block.get("text", "")
        for c in block.get("citations") or []:
          if c.get("url"):
            got["seen"].append(c["url"])
            got["cited"].append({"url": c["url"], "title": c.get("title"), "cited_text": c.get("cited_text")})
      elif kind == "web_search_tool_result":
        for r in block.get("content") or []:
          if isinstance(r, dict) and r.get("url"):
            got["seen"].append(r["url"])
    if doc.get("stop_reason") != "pause_turn":
      break
    body["messages"] = [body["messages"][0], {"role": "assistant", "content": doc.get("content")}]
  got["seen"] = sorted(set(got["seen"]))
  return got

def parse_answer(text: str) -> dict | None:
  a, b = str(text or "").find("{"), str(text or "").rfind("}")
  if a < 0 or b <= a:
    return None
  try:
    out = json.loads(text[a:b + 1])
  except json.JSONDecodeError:
    return None
  return out if isinstance(out, dict) else None

def _num(x) -> bool:
  return isinstance(x, (int, float)) and not isinstance(x, bool) and x == x

def clean_sources(sources, seen: list) -> list:
  seen_set = {canon(u) for u in seen}
  out = []
  for s in sources if isinstance(sources, list) else []:
    if not isinstance(s, dict) or not str(s.get("url") or "").strip():
      continue
    url = str(s["url"]).strip()
    out.append({"url": url, "title": str(s.get("title") or ""), "quote": str(s.get("quote") or ""), "domain": domain_of(url), "rank": rank_of(url), "url_seen": canon(url) in seen_set})
  return sorted(out, key=lambda x: x["rank"])

def checks_of(draft: dict) -> list:
  v, rng, src = draft.get("value"), draft.get("range"), draft.get("sources") or []
  out = []
  
  def add(name, ok, note):
    out.append({"name": name, "ok": bool(ok), "note": note})
  add("shape", _num(v) and (rng is None or (isinstance(rng, list) and len(rng) == 2 and all(_num(x) for x in rng) and rng[0] < rng[1])), "value is a number; a range, when given, is [low, high]")
  add("unit", unit_of(draft.get("unit")) is not None, f"unit {draft.get('unit')!r} parses" if unit_of(draft.get("unit")) else f"unit {draft.get('unit')!r} is not one of {', '.join(units())}")
  real = [s for s in src if s["url_seen"]]
  doms = sorted({s["domain"] for s in real})
  add("domains", len(doms) >= 2, f"{len(doms)} independent domain(s) among sources the search returned: {', '.join(doms) or 'none'}" + (f"; {len(src) - len(real)} named source(s) were not in the search results" if len(src) != len(real) else ""))
  hit = [s["url"] for s in real if _num(v) and has_number(s["quote"], v)]
  add("quote_number", bool(hit), f"the number {v} is in the quotation of {len(hit)} source(s)" if hit else f"the number {v} is in no quotation")
  best = min((s["rank"] for s in real), default=None)
  add("official_source", best is not None and best <= 2, "the best source is " + ("a Punjab government page" if best == 0 else "a code body" if best == 1 else "a government page" if best == 2 else "not a government or code page: a blog or trade page is never enough alone"))
  return out

def blocking(checks: list) -> list:
  return [c for c in checks if c["name"] != "official_source" and not c["ok"]]

def build_draft(card: dict, question: str, model: str, raw: dict, used: dict, key: str) -> dict:
  ans = parse_answer(raw.get("text"))
  base = {"card": card["id"], "question": question, "date": today(), "model": model, "cache_key": key, "usage": used}
  if ans is None:
    return {**base, "status": UNPARSED, "value": None, "unit": None, "range": None, "sources": [], "checks": [], "suggested_kind": None, "notes": "the answer was not one JSON object: " + str(raw.get("text") or "")[:300]}
  sources = clean_sources(ans.get("sources"), raw.get("seen") or [])
  unit = unit_of(ans.get("unit")) or ans.get("unit")
  d = {**base, "value": ans.get("value"), "unit": unit, "range": ans.get("range"), "sources": sources, "notes": str(ans.get("notes") or ""), "status": None, "checks": []}
  if ans.get("value") is None:
    d["status"], d["suggested_kind"] = NOT_FOUND, None
    return d
  
  d["checks"] = checks_of(d)
  d["status"] = FAILED if blocking(d["checks"]) else CHECKED
  best = min((s["rank"] for s in sources if s["url_seen"]), default=None)
  d["suggested_kind"] = CV.TRACE_SEED if best is None or best > 2 else ST.STANDARD
  return d

def spent_usd(now=None) -> float:
  searches = sum(int(e.get("searches") or 0) for e in CACHE.read_all(AI_CASE) if CAP.in_month(e.get("at"), now))
  return COST.cache_spent_usd(CIO.HERE, now) + COST.cache_spent_usd(DRAFTS, now) + searches * SEARCH_USD

def over_cap(spent: float, model: str, max_tokens: int, max_uses: int, cap_usd: float | None = None) -> str | None:
  cap = float(settings.ai_monthly_cap_usd if cap_usd is None else cap_usd)
  nxt = CAP.next_call_usd(model, max_tokens)
  if nxt is None:
    return CAP.check(spent, model, max_tokens, cap_usd)
  worst = nxt + max_uses * SEARCH_USD
  if spent + worst > cap:
    return f"{CAP.CAP_REACHED}: {spent:.4f} USD spent this month and the next draft may cost up to {worst:.4f} USD (tokens, and {max_uses} searches at {SEARCH_USD:g} USD), which would pass the monthly cap of {cap:g} USD (AI_MONTHLY_CAP_USD)."
  return None

def cache_key(card: dict, question: str, model: str) -> str:
  return CACHE.key(CACHE.pdf_sha256(TASK.encode()), 0, {"card": card["id"], "question": question}, TASK, PROMPT_VERSION, model)

def draft_path(card_id: str, folder: str = DRAFTS) -> str:
  return os.path.join(folder, card_id + ".yaml")

def write_draft(d: dict, folder: str = DRAFTS) -> str:
  os.makedirs(folder, exist_ok=True)
  p = draft_path(d["card"], folder)
  with open(p, "w", encoding="utf-8", newline="\n") as fh:
    fh.write("# A draft, not a standard. Written by standards_draft; a person reads the sources before it is promoted. Nothing in a run reads this file.\n")
    yaml.safe_dump(d, fh, sort_keys=False, allow_unicode=True, width=160)
  return p

def read_draft(card_id: str, folder: str = DRAFTS) -> dict | None:
  p = draft_path(card_id, folder)
  if not os.path.isfile(p):
    return None
  with open(p, encoding="utf-8") as fh:
    return yaml.safe_load(fh)

def make(card_id: str, question: str | None = None, *, model: str | None = None, max_tokens: int = MAX_TOKENS, max_uses: int = MAX_USES, fresh: bool = False, ask=None,
    folder: str = DRAFTS, now=None, cap_usd: float | None = None) -> tuple:
  card = card_of(card_id) or {"id": card_id, "name": card_id}
  q = question or card.get("question")
  if not q:
    return None, f"{card_id} has no question: give one"
  model = model or settings.ai_model_strong
  key = cache_key(card, q, model)
  there = read_draft(card["id"], folder)
  if there and there.get("promoted"):
    return there, f"already promoted by {there['promoted']['by']} on {there['promoted']['date']}; not asked again (delete the draft file by hand to start again)"
  hit = None if fresh else CACHE.read(os.path.join(folder, "_ai"), key)
  if hit is not None:
    d = build_draft(card, q, model, hit["raw"], hit["usage"], key)
    write_draft(d, folder)
    return d, "from the cache, nothing spent"
  stop = over_cap(spent_usd(now), model, max_tokens, max_uses, cap_usd)
  
  if stop:
    return None, stop
  raw = (ask or ask_api)(card, q, model, max_tokens, max_uses)
  used = {"input_tokens": raw.get("input_tokens"), "output_tokens": raw.get("output_tokens"), "searches": raw.get("searches"),
    "usd": round(CAP.usd(model, raw.get("input_tokens"), raw.get("output_tokens")) + int(raw.get("searches") or 0) * SEARCH_USD, 6)}
  CACHE.write(os.path.join(folder, "_ai"), {"cache_key": key, "at": today(), "task": TASK, "model": model, "input_tokens": raw.get("input_tokens"), "output_tokens": raw.get("output_tokens"),
    "searches": raw.get("searches"), "status": "OK", "card": card["id"], "raw": {k: raw.get(k) for k in ("text", "seen", "cited", "stop_reason")}, "usage": used})
  d = build_draft(card, q, model, raw, used, key)
  write_draft(d, folder)
  return d, f"{used['input_tokens']} in, {used['output_tokens']} out, {used['searches']} search(es), {used['usd']:.4f} USD"

def entry_text(d: dict, by: str, date: str, name: str, scope: list) -> str:
  web = [{"url": s["url"], "title": s["title"], "quote": s["quote"], "opened": d["date"]} for s in d["sources"] if s["url_seen"]]
  shape = {"range": d["range"]} if d.get("range") and d.get("value") is None else {"value": d["value"]}
  note = (f"Drafted from the web by standards_draft on {d['date']} (model {d['model']}) and promoted by {by} on {date} after reading the sources listed under web. "
    f"Suggested kind {d['suggested_kind']}: it stays a TRACE_SEED until a person pins it to a rate-book page or the QS signs it. A draft that agrees with the QS is still a draft until he signs.")
  doc = {"id": "STD_" + d["card"], "name": name, **shape, "unit": d["unit"], "scope": scope, "source": {"kind": CV.TRACE_SEED, "label": CV.SOURCE_LABELS[CV.TRACE_SEED], "note": note, "web": web}}
  body = yaml.safe_dump([doc], sort_keys=False, allow_unicode=True, width=1000)
  return "".join("  " + ln + "\n" if ln.strip() else "\n" for ln in body.splitlines())

def promote(card_id: str, by: str, *, scope: list | None = None, path: str = ST.PATH, folder: str = DRAFTS, date: str | None = None) -> tuple:
  d = read_draft(card_id, folder)
  if d is None:
    return False, f"no draft for {card_id} in {folder}"
  if d.get("status") != CHECKED:
    return False, f"{card_id} is {d.get('status')}, not {CHECKED}: only a draft that passed its checks is promoted"
  if not str(by or "").strip():
    return False, "--by names the person who read the sources"
  if d.get("promoted"):
    return False, f"{card_id} was promoted by {d['promoted']['by']} on {d['promoted']['date']}"
  with open(path, encoding="utf-8", newline="") as fh:
    before = fh.read()
    
  if any(e.get("id") == "STD_" + card_id for e in (yaml.safe_load(before) or {}).get("entries") or []):
    return False, f"STD_{card_id} is already in the library; change it by hand"
  card = card_of(card_id) or {}
  text = entry_text(d, by.strip(), date or today(), card.get("name") or card_id, scope or card.get("scope") or ["H", "P"])
  nl = "\r\n" if "\r\n" in before else "\n"
  after = before.rstrip("\r\n") + nl + text.replace("\n", nl)
  with open(path, "w", encoding="utf-8", newline="") as fh:
    fh.write(after)
  bad = ST.problems(path)
  if bad:
    with open(path, "w", encoding="utf-8", newline="") as fh:
      fh.write(before)
    return False, "the standards check refused it, so the file is as it was: " + "; ".join(bad[:3])
  d["promoted"] = {"by": by.strip(), "date": date or today()}
  write_draft(d, folder)
  return True, f"STD_{card_id} added to {os.path.basename(path)} as TRACE_SEED, with {len([s for s in d['sources'] if s['url_seen']])} web source(s)"

def line_of(d: dict | None) -> str:
  if d is None:
    return "no draft"
  v = "-" if d.get("value") is None else (f"{d['value']:g}" if _num(d["value"]) else str(d["value"]))
  fails = ", ".join(c["name"] for c in blocking(d.get("checks") or []))
  return f"{d['card']}: {d['status']}  value {v} {d.get('unit') or ''}  {len([s for s in d['sources'] if s['url_seen']])} source(s) seen" + (f"; failed: {fails}" if fails else "") + (f"; best source kind {d['suggested_kind']}" if d.get("suggested_kind") else "")

def spend_line(now=None) -> str:
  return f"spent this month {spent_usd(now):.4f} USD (case folders, drafts and searches at {SEARCH_USD:g} USD each) against a monthly cap of {settings.ai_monthly_cap_usd:g} USD"

def main(argv: list | None = None) -> int:
  a = list(sys.argv[1:] if argv is None else argv)
  help_text = ("usage: standards_draft CARD \"question\" [--model M] [--max-uses N] [--max-tokens N] [--fresh] [--dry]\n"
    "       standards_draft batch [--fresh]        every card of standards_draft_cards.yaml that has no draft\n"
    "       standards_draft promote CARD --by \"Name\" [--scope H,P]\n"
    "       standards_draft list | spend")
  if not a or a[0] in ("-h", "--help"):
    print(help_text)
    return 0
  def opt(name, default=None):
    if name in a:
      i = a.index(name)
      v = a[i + 1] if i + 1 < len(a) else default
      del a[i:i + 2]
      return v
    return default
  def flag(name):
    if name in a:
      a.remove(name)
      return True
    return False
  
  cmd = a[0] if a[0] in ("batch", "promote", "list", "spend") else "draft"
  if cmd != "draft":
    a.pop(0)
  fresh, dry = flag("--fresh"), flag("--dry")
  by, scope, model = opt("--by"), opt("--scope"), opt("--model")
  max_uses, max_tokens = int(opt("--max-uses", MAX_USES)), int(opt("--max-tokens", MAX_TOKENS))
  if cmd == "list":
    for c in cards():
      print(line_of(read_draft(c["id"])) if read_draft(c["id"]) else f"{c['id']}: no draft")
    return 0
  if cmd == "spend":
    print(spend_line())
    return 0
  if cmd == "promote":
    if not a:
      print(help_text)
      return 1
    ok, msg = promote(a[0], by or "", scope=[s.strip() for s in scope.split(",")] if scope else None)
    print(msg)
    return 0 if ok else 1
  todo = [(c["id"], c.get("question")) for c in cards() if fresh or read_draft(c["id"]) is None] if cmd == "batch" else [(a[0], a[1] if len(a) > 1 else None)] if a else []
  if not todo:
    print(help_text if cmd == "draft" else "every card has a draft; --fresh asks again")
    return 0 if cmd == "batch" else 1
  
  code = 0
  for cid, q in todo:
    if dry:
      card = card_of(cid) or {"id": cid}
      body = request_body(card, q or card.get("question") or "", model or settings.ai_model_strong, max_tokens, max_uses)
      up_to = CAP.next_call_usd(body["model"], max_tokens)
      print(f"{cid}: would ask {body['model']} with up to {max_uses} searches; at most {'n/a (model has no price)' if up_to is None else format(up_to + max_uses * SEARCH_USD, '.4f') + ' USD'}")
      continue
    d, msg = make(cid, q, model=model, max_tokens=max_tokens, max_uses=max_uses, fresh=fresh)
    print(line_of(d) + f"  [{msg}]" if d else f"{cid}: not asked: {msg}")
    if d is None:
      code = 2
      if "AI_CAP" in msg:
        break
  print(spend_line())
  return code

if __name__ == "__main__":
  sys.exit(main())
