from __future__ import annotations
from uuid import UUID, uuid5
from app.engine.measure.models import MappingInput, CalculationContext
from decimal import Decimal
from app.engine.measure import engine as kernel
from app.engine.measure.incremental import AllocationPlanner, alloc_signature, baseline_from_run, diff_elements, element_hash, equivalent, stable_keys
from app.engine.measure.conventions import get_convention
import pytest
import random
from dataclasses import replace
from app.engine.measure.synthetic import element_count, frame, grid_for, make_element, rect, reissued, shifted

NS = UUID(int=12345)
CONVENTION = "FRAME_MONOLITHIC_A"
MAPS = tuple(MappingInput(ifc_type=t, work_item_code=c, confidence_base=Decimal("0.95")) for t, c in
  (("IfcColumn", "CON-RCC"), ("IfcBeam", "CON-RCC"), ("IfcSlab", "CON-RCC"), ("IfcWall", "MAS-BRICK")))

def _ctx(n: int) -> CalculationContext:
  return CalculationContext(run_id=UUID(int=n), engine_version="x", fingerprint="f", convention_code=CONVENTION,
    rule_set_code="P", rule_set_version=1, mappings=MAPS, convention_params={})

def _run(elements, n, baseline=None, max_ratio=0.5):
  ctx = _ctx(n)
  accepted, _ = kernel.validate_input(ctx, elements)
  solids, _ = kernel.build_solids(ctx, accepted)
  planner = AllocationPlanner(ctx, get_convention(CONVENTION), solids, accepted, baseline, max_ratio)
  planner.spatial()
  planner.relations()
  alloc = planner.allocate()
  ledger, _ = kernel.measure(ctx, solids, alloc)
  return ctx, planner, alloc, ledger

def _baseline(res):
  ctx, planner, alloc, _ = res
  stored, edges = planner.state()
  return baseline_from_run(ctx.run_id, alloc_signature("x", CONVENTION, {}), stored, edges, alloc.deductions)

def _ledger_sig(ledger):
  return [(str(r.solid_id), r.work_item_code, str(r.quantity), str(r.confidence), r.trace, r.warnings) for r in ledger]

@pytest.fixture(scope="module")
def model():
  els = frame(6, 6, 4, namespace=NS)
  return els, _run(els, 1)

def _assert_same(edited, model, n, expect_mode="INCREMENTAL"):
  _, base = model
  full = _run(edited, n)
  incr = _run(edited, n, baseline=_baseline(base))
  assert equivalent(full[2], incr[2]) == []
  assert _ledger_sig(full[3]) == _ledger_sig(incr[3])
  summary = incr[1].summary()
  assert summary["mode"] == expect_mode, summary
  return incr[1]

def test_synthetic_model_size_helpers():
  nx, ny, nz = grid_for(20_000)
  assert element_count(nx, ny, nz) >= 20_000
  assert len(frame(3, 3, 2, namespace=NS)) == element_count(3, 3, 2)

def test_unchanged_model_recomputes_nothing(model):
  els, _ = model
  planner = _assert_same(list(els), model, 2)
  s = planner.summary()
  assert s["recompute"] == 0 and s["reused"] == len(els)

def test_one_column_moved(model):
  els, _ = model
  i = next(i for i, e in enumerate(els) if e.role == "COLUMN" and "|2|2|" in e.ifc_global_id)
  edited = list(els)
  edited[i] = shifted(els[i], dx=140.0, dy=-60.0)
  planner = _assert_same(edited, model, 3)
  s = planner.summary()
  assert 0 < s["recompute"] < len(els) // 4

def test_slab_deleted_and_column_added(model):
  els, _ = model
  slab = next(e for e in els if e.role == "SLAB")
  edited = [e for e in els if e.id != slab.id]
  lvl = els[0].level_id
  edited.append(make_element(NS, "extra|col", "IfcColumn", "COLUMN", lvl, rect(5000 - 80, 5000 - 80, 5000 + 220, 5000 + 220), 0.0, 3000.0))
  _assert_same(edited, model, 4)

def test_role_only_change(model):
  els, _ = model
  j = next(i for i, e in enumerate(els) if e.role == "BEAM")
  edited = list(els)
  edited[j] = replace(els[j], role="EDGE_BEAM")
  _assert_same(edited, model, 5)

@pytest.mark.parametrize("seed", [1, 2, 3])
def test_new_revision_with_reminted_row_ids(model, seed):
  els, _ = model
  ns = uuid5(NS, f"rev{seed}")
  _assert_same(reissued(list(els), ns), model, 10 + seed)

def test_revision_with_edits_and_new_ids(model):
  els, _ = model
  rng = random.Random(7)
  edited = list(els)
  for i in rng.sample(range(len(edited)), 12):
    if edited[i].role == "COLUMN":
      edited[i] = shifted(edited[i], dx=rng.choice([-150.0, 90.0, 200.0]))
  _assert_same(reissued(edited, uuid5(NS, "rev-edit")), model, 20)

def test_many_edits_over_ratio_fall_back_to_full(model):
  els, _ = model
  edited = [shifted(e, dx=40.0) if i % 2 == 0 else e for i, e in enumerate(els)]
  _, base = model
  incr = _run(edited, 30, baseline=_baseline(base), max_ratio=0.2)
  assert incr[1].summary()["mode"] == "FULL"
  assert incr[1].fallback_reason
  full = _run(edited, 30)
  assert equivalent(full[2], incr[2]) == []

def test_signature_mismatch_falls_back_to_full(model):
  els, _ = model
  _, base = model
  stale = _baseline(base)
  stale.signature = alloc_signature("y", CONVENTION, {})
  incr = _run(list(els), 31, baseline=stale)
  assert incr[1].summary()["mode"] == "FULL"
  assert incr[1].fallback_reason == "ALLOCATION_INPUTS_CHANGED"

def test_missing_baseline_is_a_full_run(model):
  els, _ = model
  incr = _run(list(els), 32, baseline=None)
  assert incr[1].summary()["mode"] == "FULL"

def test_duplicate_global_ids_get_distinct_keys():
  a = make_element(NS, "dup", "IfcColumn", "COLUMN", None, rect(0, 0, 300, 300), 0.0, 3000.0)
  b = replace(a, id=uuid5(NS, "other"))
  keys = stable_keys([a, b])
  assert len(set(keys.values())) == 2

def test_element_hash_ignores_row_id_but_not_geometry():
  a = make_element(NS, "h", "IfcColumn", "COLUMN", None, rect(0, 0, 300, 300), 0.0, 3000.0)
  assert element_hash(a) == element_hash(replace(a, id=uuid5(NS, "x")))
  assert element_hash(a) != element_hash(shifted(a, dx=1.0))

def test_diff_elements_reports_added_removed_changed(model):
  els, base = model
  baseline = _baseline(base)
  edited = list(els)
  edited[0] = shifted(els[0], dx=25.0)
  gone = edited.pop(5)
  edited.append(make_element(NS, "new|1", "IfcColumn", "COLUMN", els[0].level_id, rect(9000, 9000, 9300, 9300), 0.0, 3000.0))
  keys = stable_keys(edited)
  change = diff_elements({keys[e.id]: element_hash(e) for e in edited}, baseline)
  assert change.added == 1 and change.removed == 1 and change.modified == 1
  assert len(change.changed) == 2 and len(change.gone) == 1