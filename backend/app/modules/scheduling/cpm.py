from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, timedelta
from uuid import UUID

@dataclass
class TaskInput:
  id: UUID
  planned_start_date: date | None
  planned_duration_days: int
  predecessor_ids: list[UUID] = field(default_factory=list)

@dataclass
class TaskComputed:
  task_id: UUID
  is_computable: bool
  earliest_start: date | None = None
  earliest_finish: date | None = None
  latest_start: date | None = None
  latest_finish: date | None = None
  total_float_days: int | None = None
  is_critical: bool = False

@dataclass
class CPMResult:
  tasks: dict[UUID, TaskComputed]
  natural_completion_date: date | None
  target_completion_date: date | None
  days_ahead_or_behind_target: int | None  
  warnings: list[str]

def _duration_span(duration_days: int) -> timedelta:
  return timedelta(days=max(duration_days, 0) - 1 if duration_days > 0 else 0)

def compute_cpm(
  tasks: list[TaskInput],
  target_completion_date: date | None = None,
) -> CPMResult:
  warnings: list[str] = []
  by_id = {task.id: task for task in tasks}
  successors: dict[UUID, list[UUID]] = {task.id: [] for task in tasks}
  in_degree: dict[UUID, int] = {task.id: 0 for task in tasks}

  for task in tasks:
    for pred_id in task.predecessor_ids:
      if pred_id not in by_id:
        warnings.append(f"Task {task.id} references a predecessor that no longer exists; ignored.")
        continue
      successors[pred_id].append(task.id)
      in_degree[task.id] += 1

  queue = [tid for tid, degree in in_degree.items() if degree == 0]
  topo_order: list[UUID] = []
  remaining_in_degree = dict(in_degree)

  while queue:
    current = queue.pop(0)
    topo_order.append(current)
    for succ_id in successors[current]:
      remaining_in_degree[succ_id] -= 1
      if remaining_in_degree[succ_id] == 0:
        queue.append(succ_id)

  if len(topo_order) != len(tasks):
    warnings.append(
      "A circular dependency was detected in this schedule -- some tasks could not be "
      "scheduled. This should not be possible; please report it."
    )
    cyclic_ids = set(by_id.keys()) - set(topo_order)
    topo_order += list(cyclic_ids)

  computed: dict[UUID, TaskComputed] = {}

  for task_id in topo_order:
    task = by_id[task_id]
    if not task.predecessor_ids:
      if task.planned_start_date is None:
        computed[task_id] = TaskComputed(task_id=task_id, is_computable=False)
        warnings.append(f"'{task_id}' has no predecessors and no planned start date, so it can't be scheduled yet.")
        continue
      earliest_start = task.planned_start_date
    else:
      pred_finishes = []
      unresolved = False
      for pred_id in task.predecessor_ids:
        pred_computed = computed.get(pred_id)
        if pred_computed is None or not pred_computed.is_computable:
          unresolved = True
          break
        pred_finishes.append(pred_computed.earliest_finish)
      if unresolved:
        computed[task_id] = TaskComputed(task_id=task_id, is_computable=False)
        continue
      earliest_start = max(pred_finishes) + timedelta(days=1)

    earliest_finish = earliest_start + _duration_span(task.planned_duration_days)
    computed[task_id] = TaskComputed(
      task_id=task_id, is_computable=True, earliest_start=earliest_start, earliest_finish=earliest_finish,
    )

  computable_finishes = [c.earliest_finish for c in computed.values() if c.is_computable]
  natural_completion = max(computable_finishes) if computable_finishes else None

  anchor_finish = natural_completion
  days_ahead_or_behind: int | None = None
  if natural_completion is not None and target_completion_date is not None:
    days_ahead_or_behind = (target_completion_date - natural_completion).days
    if target_completion_date > natural_completion:
      anchor_finish = target_completion_date
    else:
      warnings.append(
        f"The critical path currently finishes {abs(days_ahead_or_behind)} day(s) "
        f"after the target completion date."
      )

  for task_id in reversed(topo_order):
    result = computed[task_id]
    if not result.is_computable:
      continue
    task = by_id[task_id]
    succ_ids = [s for s in successors[task_id] if computed.get(s) and computed[s].is_computable]

    if not succ_ids:
      latest_finish = anchor_finish
    else:
      latest_starts = [computed[s].latest_start for s in succ_ids]
      latest_finish = min(latest_starts) - timedelta(days=1)

    latest_start = latest_finish - _duration_span(task.planned_duration_days)
    result.latest_start = latest_start
    result.latest_finish = latest_finish
    result.total_float_days = (latest_start - result.earliest_start).days
    result.is_critical = result.total_float_days <= 0

  return CPMResult(
    tasks=computed, natural_completion_date=natural_completion, target_completion_date=target_completion_date,
    days_ahead_or_behind_target=days_ahead_or_behind, warnings=warnings,
  )