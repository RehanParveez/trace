from __future__ import annotations
from app.modules.drawings_boq.takeoff.proof.reading import score as SCR

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

REGISTER_ORDER = ("role", "plan_kind", "floor", "discipline", "scale_basis", "scale_ratio", "sheet_no", "title", "text_type")

def register_fields(outcomes: list) -> dict:
  out: dict = {}
  for o in outcomes:
    parts = o["id"].split(":")
    if len(parts) == 4 and parts[1] == "REG":
      row = out.setdefault(parts[3], {"right": 0, "wrong": 0})
      row["right" if o["outcome"] == SCR.OK else "wrong"] += 1
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
  out = [f"# Reading score: {doc['split']}", "", f"Reading hash `{doc['hash']}`. {len(doc['sets'])} PDF(s) scored, {len(doc['outcomes'])} outcomes. Silent-wrong is pessimistic until RB-B2: every item counts as READ.", ""]
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
  params = [s for s in doc["sets"] if s["params"]["inputs"]]
  if params:
    out += ["## Input completeness (parameter ledger)", "", "| PDF | Inputs | PRINTED | DERIVED | DEFAULTED | MISSING | Share printed or derived |", "|---|---|---|---|---|---|---|"]
    for s in params:
      p = s["params"]
      out.append(f"| {s['alias']} | {p['inputs']} | {p['states']['PRINTED']} | {p['states']['DERIVED']} | {p['states']['DEFAULTED']} | {p['states']['MISSING']} | {_pct(p['complete'])} |")
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
