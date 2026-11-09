from __future__ import annotations

def money(v) -> str:
  return "-" if v is None else f"{float(v):,.0f}"

def markdown(r: dict) -> str:
  p = r["project"]
  out = [f"# {r['title']}", "", f"{p.get('name') or p.get('case') or ''}" + (f" · {r['generated']}" if r.get("generated") else ""), "", r["intro"], ""]
  c = r["coverage"]
  out += ["## 1. What was read", "", "| Section | Measured | Assumed | Asked | Not read | With a quantity |", "|---|---|---|---|---|---|"]
  for s in c["sections"]:
    out.append(f"| {s['section']} | {s['MEASURED']} | {s['ASSUMED']} | {s['ASKED']} | {s['NOT_READ']} | {s['with_quantity_pct']:.1f}% |")
  t = c["total"]
  out += [f"| **All** | {t['MEASURED']} | {t['ASSUMED']} | {t['ASKED']} | {t['NOT_READ']} | {t['with_quantity_pct']:.1f}% |", ""]
  if c["note"]:
    out += [c["note"], ""]
    for n in c["not_read_items"]:
      out.append(f"- {n['section']}: {', '.join(n['items'])}" + (f" and {n['more']} more" if n["more"] else ""))
    out.append("")
    
  m = r["money"]
  out += ["## 2. The money", ""]
  if m["priced"]:
    out += [f"Total of the priced lines: {money(m['total'])}. Measured: {money(m['measured'])}. Resting on assumptions: {money(m['assumed'])} ({m['assumed_pct']}%). Lines with no rate: {m['unpriced_lines']} of {m['lines']}.", ""]
  else:
    out += [m["note"], f"{m['lines']} lines: {m['measured_lines']} measured, {m['assumed_lines']} resting wholly or partly on assumptions.", ""]
  cf = r["confidence"]
  out += ["## 3. How sure Trace is", ""]
  if cf["shown"]:
    out += ["| Confidence | Lines | " + ("Money" if cf["basis"] == "MONEY" else "Share of lines") + " | Share |", "|---|---|---|---|"]
    out += [f"| {b['band']} | {b['lines']} | {money(b['amount']) if b['amount'] is not None else ''} | {b['pct']}% |" for b in cf["bands"]]
    out.append("")
    
  else:
    out += [cf["why"], ""]
  q = r["questions"]
  out += [f"## 4. Open questions ({q['open']})", ""]
  if q["open"]:
    out += [f"Money waiting on them: {money(q['money'])}" + (f"; {q['unvalued']} have no money figure" if q["unvalued"] else "") if q["money"] is not None else f"No money figure: {q['unvalued']} question(s) are not priced.", "",
      "| Question | Sheet | Items changed | Effect |", "|---|---|---|---|"]
    out += [f"| {x['item']}: {x['prompt']} | {x['page'] or ''} | {x['touches']} | {money(x['effect_rs'])} |" for x in q["rows"]]
    if q["more"]:
      out.append(f"{q['more']} more are in the review list.")
  else:
    out.append("No review row is open.")
  a = r["assumptions"]
  out += ["", f"## 5. Assumptions and where they come from ({a['count']})", ""]
  if a["rows"]:
    out += ["| Input | Figure used | Range | Source | Items |", "|---|---|---|---|---|"]
    out += [f"| {x['input'].replace('_', ' ')} | {x['value']} {x['unit'] or ''} | {'-' if not x['range'] else str(x['range'][0]) + ' to ' + str(x['range'][1])} | {x['source'] or ''} | {x['items']} |" for x in a["rows"]]
    if a["more"]:
      out.append(f"{a['more']} more.")
  else:
    out.append("No quantity rests on an assumed input.")
  k = r["check_first"]
  out += ["", "## 6. Check these first", "", k["text"], ""]
  if k["lines"]:
    out += ["| Line | Floor | Amount | Band | Open rows | Sheets | Crop |", "|---|---|---|---|---|---|---|"]
    out += [f"| {x['code']} {x['description'] or ''} | {x['floor'] or ''} | {money(x['amount'])} | {x['band'] or ''} | {x['open_rows']} | {', '.join(str(p) for p in x['pages'])} | {x['crop_url'] or 'none'} |" for x in k["lines"]]
  else:
    out.append("Nothing to check first.")
  tr = r["track_record"]
  out += ["", "## 7. Track record", "", tr["text"], tr["rule"]]
  if tr["unscored_sets"]:
    out.append(f"Entered as first sight and not yet scored: {', '.join(tr['unscored_sets'])}.")
  out += ["", r["footer"], ""]
  return "\n".join(out)
