from __future__ import annotations
from app.modules.drawings_boq.takeoff.proof.reading import score as SCR
from app.modules.drawings_boq.takeoff.proof.reading import settings as ST

def _pct(v) -> str:
  return "-" if v is None else f"{v * 100:.1f}%"

def _ci(pair) -> str:
  return "" if not pair or pair[0] is None else f" ({pair[0] * 100:.0f}-{pair[1] * 100:.0f})"

def _row(name: str, t: dict) -> str:
  return (f"| {name} | {t['truth']} | {t['matched']} | {_pct(t['recall'])}{_ci(t['recall_ci'])} | {_pct(t['value_accuracy'])} | {t['judged_reads']} | {_pct(t['precision'])}{_ci(t['precision_ci'])} | "
    f"{t['silent_wrong']} ({_pct(t['silent_wrong_rate'])}) | {_pct(t['honest_unread'])} |")

HEAD = ["| Class | Truth items | Matched | Recall (95% interval) | Value accuracy | Read items judged | Precision | Silent-wrong | Honest-unread |", "|---|---|---|---|---|---|---|---|---|"]

def worst_sheets(outcomes: list, n: int = 20) -> list:
  score: dict = {}
  for o in outcomes:
    if o["outcome"] in (SCR.MISSED_S, SCR.WRONG, SCR.INV_S):
      k = (o["set"], o["sheet"])
      score[k] = score.get(k, 0) + 1
  return sorted(score.items(), key=lambda kv: (-kv[1], kv[0][0], str(kv[0][1])))[:n]

def by_set_lines(doc: dict) -> list:
  rows: dict = {}
  for o in doc["outcomes"]:
    rows.setdefault(o["set"], []).append(o)
  out = [f"  {'PDF':<30} {'truth':>6} {'matched':>8} {'recall':>8} {'silent-wrong':>13}"]
  for s in sorted(doc["sets"], key=lambda s: s["alias"]):
    rs = rows.get(s["alias"])
    if not rs:
      out.append(f"  {s['alias']:<30} {'no truth written':>38}")
      continue
    t = SCR._tally(rs)
    out.append(f"  {s['alias']:<30} {t['truth']:>6} {t['matched']:>8} {_pct(t['recall']):>8} {t['silent_wrong']:>13}")
  return out

def quality_lines(doc: dict) -> list:
  rows = [s for s in doc["sets"] if s.get("truth_quality")]
  if not rows:
    return []
  out = ["## Truth quality (how much of each set's truth a person has checked)", "", "| PDF | Truth rows | Draft rows | Checked | Checked share | Sample round | Judged | Wrong | Wrong share | Cannot tell | Status |", "|---|---|---|---|---|---|---|---|---|---|---|"]
  for s in rows:
    q = s["truth_quality"]
    out.append(f"| {s['alias']} | {q['truth_rows']} | {q['draft_rows']} | {q['checked_rows']} | {_pct(q['checked_share'])} | {q['round'] or '-'} | {q['judged']} | {q['wrong']} | {_pct(q['wrong_share'])} | {q['cannot_tell']} | {q['status']} |")
  out += ["", f"A set whose latest sample has more than {ST.wrong_share_limit() * 100:g}% wrong is REDRAFT and is left out of rule evidence until it is re-drafted and sampled again. UNCHECKED: no sample has been judged. PARTIAL: fewer than {ST.sample_min()} rows (or the whole set, if smaller) judged. Draw one with `proof.reading sample`.", ""]
  return out

STAGES = ("FIND", "READ", "JOIN", "MEASURE")

def miss_rows(doc: dict) -> list:
  return [o for o in doc["outcomes"] if o["side"] == "truth" and o["outcome"] != SCR.OK and o["class"] != "BBS_FINDING"]

def stage_summary(doc: dict) -> str:
  misses = miss_rows(doc)
  by = {s: sum(1 for o in misses if o.get("stage") == s) for s in STAGES}
  return f"  misses by stage: {len(misses)} truth items not MATCHED_OK; " + ", ".join(f"{s} {n}" for s, n in by.items()) + f"; no stage {len(misses) - sum(by.values())}"

def stage_lines(doc: dict) -> list:
  misses = miss_rows(doc)

  if not misses:
    return []
  by_set: dict = {}

  for o in misses:
    slot = by_set.setdefault(o["set"], {"misses": 0, **{s: 0 for s in STAGES}, "none": 0})
    slot["misses"] += 1
    slot[o.get("stage") or "none"] += 1
  out = ["## Misses by stage (every truth item that is not MATCHED_OK)", "", "| PDF | Misses | FIND | READ | JOIN | MEASURE | No stage |", "|---|---|---|---|---|---|---|"]
  for name in sorted(by_set):
    r = by_set[name]
    out.append(f"| {name} | {r['misses']} | {r['FIND']} | {r['READ']} | {r['JOIN']} | {r['MEASURE']} | {r['none']} |")
  tot = {k: sum(r[k] for r in by_set.values()) for k in ("misses", *STAGES, "none")}
  out.append(f"| all | {tot['misses']} | {tot['FIND']} | {tot['READ']} | {tot['JOIN']} | {tot['MEASURE']} | {tot['none']} |")
  basis: dict = {}
  for o in misses:
    basis[o.get("stage_basis") or "none"] = basis.get(o.get("stage_basis") or "none", 0) + 1
  out += ["", "How each stage was decided: " + ", ".join(f"{k} {v}" for k, v in sorted(basis.items())) + ". `region`: the truth item lies in a region of regions.yaml and Trace did or did not read anything of that kind there; `class`: no region truth covers it, so FIND means nothing of its class was read on that sheet; `matched`: Trace matched it but with a wrong value; `join`, `join_source`, `register`, `fact`: by the kind of truth row.", ""]
  by_cs: dict = {}
  for o in misses:
    k = (o["class"], o.get("stage") or "none")
    by_cs[k] = by_cs.get(k, 0) + 1

  out += ["The 20 largest groups of misses, by class and stage:", "", "| Class | Stage | Misses |", "|---|---|---|"]
  out += [f"| {c} | {s} | {n} |" for (c, s), n in sorted(by_cs.items(), key=lambda kv: (-kv[1], kv[0]))[:20]]
  out.append("")
  return out

def region_lines(doc: dict) -> list:
  regions = doc.get("regions") or {}
  
  if not any(r["rows"] for r in regions.values()):
    return ["## Region score", "", "No set has a regions.yaml yet; draft them with `proof.reading regions-draft --write`.", ""]
  out = ["## Region score (truth regions against what Trace read in them)", "", "| PDF | Kind | Truth regions | Found | Missed | Split | Merged |", "|---|---|---|---|---|---|---|"]
  for name in sorted(regions):
    for kind, r in sorted(regions[name]["by_kind"].items()):
      out.append(f"| {name} | {kind} | {r['truth']} | {r['FOUND']} | {r['MISSED']} | {r['SPLIT']} | {r['MERGED']} |")
  by_text: dict = {}
  
  for r in regions.values():
    for tt, s in (r.get("by_text_type") or {}).items():
      slot = by_text.setdefault(tt, {"truth": 0, "FOUND": 0, "MISSED": 0, "SPLIT": 0, "MERGED": 0})
      for k in slot:
        slot[k] += s[k]
  if by_text:
    out += ["", "By the text the region holds (TEXT: the text layer; OUTLINED: read from outlined letters; RASTER: read from a picture; MIXED; NONE: no word in it and no page type):", "", "| Text type | Truth regions | Found | Missed | Split | Merged |", "|---|---|---|---|---|---|"]
    out += [f"| {tt} | {s['truth']} | {s['FOUND']} | {s['MISSED']} | {s['SPLIT']} | {s['MERGED']} |" for tt, s in sorted(by_text.items())]
  basis: dict = {}
  for r in regions.values():
    for row in r["rows"]:
      basis[row["basis"]] = basis.get(row["basis"], 0) + 1
  reported = sum(r["reported_regions"] for r in regions.values())
  own = any(r.get("from_model") for r in regions.values())
  if own:
    why = f"Trace reports its own regions ({reported} reported). A truth region is FOUND when a reported region of its kind holds it (half of it inside, or its centre inside); MERGED when every such region also holds another truth region of that kind; SPLIT when no region holds it but two or more lie mostly inside it. A SCHEDULE truth region also counts a SECTION_PICTURE report (assumed: a column schedule is often drawn as a row of section sketches). A region the pages did not report is also FOUND when a read item of its kind lies in it (`inside`)."
  else:
    why = f"Trace reports no region of its own in this run ({reported} reported), so a region is FOUND when a read item of the right kind lies inside it (`inside`), or, for items with no position, when it is the only region of its kind on the sheet and one is read (`class`)."
  out += ["", "Found by: " + ", ".join(f"{k} {v}" for k, v in sorted(basis.items())) + ". " + why + " The regions are drafted from truth item positions and are not yet checked by a person.", ""]
  return out

REGISTER_ORDER = ("role", "plan_kind", "floor", "discipline", "scale_basis", "scale_ratio", "sheet_no", "title", "text_type")

def register_fields(outcomes: list) -> dict:
  out: dict = {}
  for o in outcomes:
    parts = o["id"].split(":")
    if len(parts) == 4 and parts[1] == "REG":
      row = out.setdefault(parts[3], {"right": 0, "wrong": 0})
      row["right" if o["outcome"] == SCR.OK else "wrong"] += 1
  return out

def join_kinds(outcomes: list) -> dict:
  out: dict = {}
  for o in outcomes:
    parts = o["id"].split(":")
    if len(parts) == 4 and parts[1] == "JOIN":
      row = out.setdefault(parts[2], {})
      row[o["outcome"]] = row.get(o["outcome"], 0) + 1
  return out

def worst_register_rows(outcomes: list, n: int = 15) -> list:
  wrong: dict = {}
  for o in outcomes:
    parts = o["id"].split(":")
    if len(parts) == 4 and parts[1] == "REG" and o["outcome"] != SCR.OK:
      wrong.setdefault((o["set"], o["sheet"]), []).append(o["detail"] or parts[3])
  return sorted(wrong.items(), key=lambda kv: (-len(kv[1]), kv[0][0], kv[0][1]))[:n]

def render(doc: dict, cmp: dict | None = None) -> str:
  m = doc["metrics"]
  out = [f"# Reading score: {doc['split']}", "", f"Reading hash `{doc['hash']}`. {len(doc['sets'])} PDF(s) scored, {len(doc['outcomes'])} outcomes. Silent-wrong counts wrong values and inventions among items read with status READ, and every wrong register field (a register field has no status); its rate is over the read items judged plus the register fields judged.", ""]
  if not doc["outcomes"]:
    out += ["No truth has been written for the scored PDFs, so there is nothing to judge.", ""]
  for sp, t in m["by_split"].items():
    out += [f"## Split {sp}", "", *HEAD, _row("all classes", t)]
    for key, row in m["by_split_class"].items():
      if key.startswith(sp + "|"):
        out.append(_row(key.split("|", 1)[1], row))
    out.append("")
    
  if m["by_set"]:
    out += ["## By set", "", *HEAD]
    out += [_row(k.replace("|", " "), v) for k, v in m["by_set"].items()]
    out.append("")
  if m["by_style"]:
    out += ["## By style (consultant, producer)", "", *HEAD]
    out += [_row(k, v) for k, v in m["by_style"].items()]
    out.append("")
  bf = m.get("bbs_finding")
  if bf:
    out += ["## Bar schedule audit (class BBS_FINDING)", "", f"Finding recall {_pct(bf['recall'])} ({bf['raised']} of {bf['expected']} expected raises); class accuracy {_pct(bf['class_accuracy'])}; false-error rate {_pct(bf['false_error_rate'])} "
      f"({bf['errors_outside_items']} of {bf['errors_raised']} ERRORs raised are named by no item; {bf['errors_silent']} of them are not even held in accepted_errors).", ""]
  out += quality_lines(doc)
  out += stage_lines(doc)
  out += region_lines(doc)
  params = [s for s in doc["sets"] if s["params"]["inputs"]]
  if params:
    out += ["## Input completeness (parameter ledger)", "", "| PDF | Inputs | PRINTED | DERIVED | DEFAULTED | MISSING | Share printed or derived | Supplied by what Trace read |", "|---|---|---|---|---|---|---|---|"]
    for s in params:
      p = s["params"]
      out.append(f"| {s['alias']} | {p['inputs']} | {p['states']['PRINTED']} | {p['states']['DERIVED']} | {p['states']['DEFAULTED']} | {p['states']['MISSING']} | {_pct(p['complete'])} | {(p.get('supply') or {}).get('supplied', 0)} of {(p.get('supply') or {}).get('of', 0)} |")
    out.append("")
  fields = register_fields(doc["outcomes"])
  
  if fields:
    out += ["## Register accuracy by field (Trace's own identity against the checked register)", "", "| Field | Rows judged | Right | Accuracy (95% interval) |", "|---|---|---|---|"]
    for name in [n for n in REGISTER_ORDER if n in fields]:
      f = fields[name]
      n_all = f["right"] + f["wrong"]
      out.append(f"| {name} | {n_all} | {f['right']} | {_pct(f['right'] / n_all)}{_ci(SCR.wilson(f['right'], n_all))} |")
    out += ["", "The 15 sheets with most wrong fields:", "", "| PDF | Sheet | Wrong fields (truth against Trace) |", "|---|---|---|"]
    out += [f"| {s} | {sh} | {'; '.join(d)} |" for (s, sh), d in worst_register_rows(doc["outcomes"])]
    out.append("")
  joins = join_kinds(doc["outcomes"])
  if joins:
    out += ["## Joins (the truth joins read back)", "", "| Join | Truth joins | Joined to the right target | Joined wrongly (silent) | Missing, assumed or unsure (reported) | Not read or not attempted (silent) |", "|---|---|---|---|---|---|"]
    out += [f"| {k} | {sum(v.values())} | {v.get(SCR.OK, 0)} | {v.get(SCR.WRONG, 0)} | {v.get(SCR.MISSED_R, 0)} | {v.get(SCR.MISSED_S, 0)} |" for k, v in joins.items()]
    out.append("")
  worst = worst_sheets(doc["outcomes"])
  
  if worst:
    out += ["## The 20 worst sheets", "", "| PDF | Sheet | Silent-wrong or missed items |", "|---|---|---|"]
    out += [f"| {s} | {sh} | {n} |" for (s, sh), n in worst]
    out.append("")
  if doc["unmapped"]:
    out += ["## Item kinds with no vocabulary class (read, not scored)", "", ", ".join(f"{k} {n}" for k, n in doc["unmapped"].items()), ""]
  if cmp is not None:
    out += ["## Since the baseline", "", f"Truth {'unchanged' if cmp['same_truth'] else 'changed'}; {len(cmp['changed'])} outcome(s) changed; {len(cmp['lost'])} lost.", ""]
    out += [f"- {i}: {a} to {b}" for i, a, b in cmp["changed"][:60]]
    out.append("")
  return "\n".join(out)

def render_set_join(docs: list) -> str:
  out = ["# Structure set joined to the architecture set", ""]
  if not docs:
    return "\n".join(out + ["No case has two PDFs.", ""])
  for d in docs:
    out += [f"## {d['case']}: {d['a']} (structure) with {d['b']} (architecture)", ""]
    ia, ib = d["identity"]["a"], d["identity"]["b"]
    out += [f"Title blocks: structure prints {ia}; architecture prints {ib}. {'Paired' if d['pair']['paired'] else 'Not paired'}: {d['pair']['why']}.", ""]
    al = d.get("alignment")
    if al:
      out += [f"Alignment: {al['basis']}, {al['status']}. Residual after the fit: {'-' if al.get('residual_in') is None else str(al['residual_in']) + ' in'}. {al.get('why') or ''}", ""]
      if al.get("fit"):
        f = al["fit"]
        out += [f"Fit (outline a to b): scale {f['scale']}, rotation {f['rotation']} degrees, shared points {f['n']}; outline a {al.get('outline_a_mm')} mm, outline b {al.get('outline_b_mm')} mm.", ""]
    lv = d.get("levels")
    
    if lv:
      out += ["| Floor | Level above the road (ft) | Storey height from the floor below (ft) | State |", "|---|---|---|---|"]
      for f in lv["floors"]:
        h = f["storey_height_mm"]
        out.append(f"| {f['floor']} | {'-' if f['level_ft'] is None else f['level_ft']} | {'-' if h is None else round(h / 304.8, 2)} | {f['state']} |")
      out += ["", f"Plinth level: {'not read' if lv.get('plinth_mm') is None else str(round(lv['plinth_mm'] / 304.8, 2)) + ' ft'}.", ""]
    sl = d.get("slab")
    if sl:
      shown = "; ".join(f"{v['inches']:g} in at " + ", ".join(f"{w['set']} p{w['page']} ({w['kind'].lower()})" for w in v["printed"]) for v in sl["values"]) or "none printed"
      out += [f"Slab thickness printed: {shown}. {'CONFLICT: the plans print ' + str(sl['captions_in']) + ' in and the notes ' + str(sl['notes_in']) + ' in.' if sl['conflict'] else 'No conflict.'}", ""]
    cw = d.get("columns_in_walls")
    if cw:
      out += [f"Columns inside architecture walls: {'not reported (' + cw['why'] + ')' if cw['share'] is None else str(round(cw['share'] * 100)) + '% of ' + str(cw['columns'])}.", ""]
    lg = d.get("ledger")
    if lg:
      out += [f"Parameter ledger of the structure set: share printed or derived {lg['before']} before, {lg['after']} after; now derived: {', '.join(lg['derived']) or 'none'}.", ""]
  return "\n".join(out)
