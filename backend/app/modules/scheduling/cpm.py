from __future__ import annotations
import math
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

@dataclass(frozen=True)
class WorkCalendar:
  """Which days work happens. work_week_days: 7 = every day, 6 = Monday-Saturday (Sunday off), 5 = Monday-Friday."""
  work_week_days: int = 6
  holidays: frozenset[date] = frozenset()

  def is_workday(self, day: date) -> bool:
    return day.weekday() < self.work_week_days and day not in self.holidays

  def next_workday(self, day: date) -> date:
    for _ in range(800):
      if self.is_workday(day):
        return day
      day += timedelta(days=1)
    return day

  def prev_workday(self, day: date) -> date:
    for _ in range(800):
      if self.is_workday(day):
        return day
      day -= timedelta(days=1)
    return day

  def add_workdays(self, day: date, count: int) -> date:
    day = self.next_workday(day)
    for _ in range(max(count, 0)):
      day = self.next_workday(day + timedelta(days=1))
    return day

  def sub_workdays(self, day: date, count: int) -> date:
    day = self.prev_workday(day)
    for _ in range(max(count, 0)):
      day = self.prev_workday(day - timedelta(days=1))
    return day

  def workdays_between(self, start: date, end: date) -> int:
    """Working days from start up to (not including) end; negative if end is earlier."""
    if end < start:
      return -self.workdays_between(end, start)
    return sum(1 for i in range((end - start).days) if self.is_workday(start + timedelta(days=i)))

@dataclass
class TaskInput:
  id: UUID
  planned_start_date: date | None
  planned_duration_days: int
  predecessor_ids: list[UUID] = field(default_factory=list)
  actual_start_date: date | None = None
  actual_end_date: date | None = None
  percent_complete: Decimal = Decimal("0")

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
  is_complete: bool = False

@dataclass
class CPMResult:
  tasks: dict[UUID, TaskComputed]
  natural_completion_date: date | None
  target_completion_date: date | None
  days_ahead_or_behind_target: int | None
  warnings: list[str]

def compute_cpm(
  tasks: list[TaskInput],
  target_completion_date: date | None = None,
  calendar: WorkCalendar | None = None,
  data_date: date | None = None,
) -> CPMResult:
  
  cal = calendar or WorkCalendar(work_week_days=7)
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
     
    )
    topo_order += list(set(by_id.keys()) - set(topo_order))

  def finish_after(start: date, working_days: int) -> date:
    return start if working_days <= 0 else cal.add_workdays(start, working_days - 1)

  computed: dict[UUID, TaskComputed] = {}
  work_start: dict[UUID, date] = {}      
  remaining_days: dict[UUID, int] = {}

  for task_id in topo_order:
    task = by_id[task_id]
    pct = Decimal(str(task.percent_complete or 0))
    is_complete = task.actual_end_date is not None or pct >= 100

    if is_complete:
      finish = task.actual_end_date or data_date or task.actual_start_date or task.planned_start_date
      if finish is None:
        computed[task_id] = TaskComputed(task_id=task_id, is_computable=False)
        continue
      start = task.actual_start_date or task.planned_start_date or finish
      computed[task_id] = TaskComputed(
        task_id=task_id, is_computable=True, earliest_start=min(start, finish), earliest_finish=finish, is_complete=True,
      )
      continue

    pred_finishes: list[date] = []
    unresolved = False
    for pred_id in task.predecessor_ids:
      if pred_id not in by_id:
        continue
      
      pred = computed.get(pred_id)
      if pred is None or not pred.is_computable:
        unresolved = True
        break
      pred_finishes.append(pred.earliest_finish)
    if unresolved:
      computed[task_id] = TaskComputed(task_id=task_id, is_computable=False)
      continue

    if task.actual_start_date is not None:
      remaining = math.ceil(task.planned_duration_days * float(100 - pct) / 100)
      anchor = max(data_date, task.actual_start_date) if data_date else task.actual_start_date
      start_of_rest = cal.next_workday(anchor)
      
      computed[task_id] = TaskComputed(
        task_id=task_id, is_computable=True, earliest_start=task.actual_start_date,
        earliest_finish=finish_after(start_of_rest, remaining) if remaining > 0 else anchor,
      )
      work_start[task_id] = start_of_rest
      remaining_days[task_id] = remaining
      continue

    candidates: list[date] = []
    if pred_finishes:
      candidates.append(max(pred_finishes) + timedelta(days=1))
      
    if task.planned_start_date is not None:
      candidates.append(task.planned_start_date)
    if not candidates:
      computed[task_id] = TaskComputed(task_id=task_id, is_computable=False)
      warnings.append(f"'{task_id}' has no predecessors and no planned start date, so it can't be scheduled yet.")
      continue
    
    if data_date is not None:
      candidates.append(data_date)
    earliest_start = cal.next_workday(max(candidates))
    computed[task_id] = TaskComputed(
      task_id=task_id, is_computable=True, earliest_start=earliest_start,
      earliest_finish=finish_after(earliest_start, task.planned_duration_days),
    )
    work_start[task_id] = earliest_start
    remaining_days[task_id] = task.planned_duration_days

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
        f"The critical path currently finishes {abs(days_ahead_or_behind)} day(s) after the target completion date."
      )

  for task_id in reversed(topo_order):
    result = computed[task_id]
    if not result.is_computable or result.is_complete:
      continue
    live_successors = [
      s for s in successors[task_id] if computed.get(s) and computed[s].is_computable and not computed[s].is_complete
    ]
    
    if not live_successors:
      latest_finish = cal.prev_workday(anchor_finish)
    else:
      latest_finish = cal.prev_workday(min(computed[s].latest_start for s in live_successors) - timedelta(days=1))
    span = remaining_days[task_id]
    latest_start = latest_finish if span <= 0 else cal.sub_workdays(latest_finish, span - 1)
    result.latest_start = latest_start
    result.latest_finish = latest_finish
    result.total_float_days = cal.workdays_between(work_start[task_id], latest_start)
    result.is_critical = result.total_float_days <= 0

  return CPMResult(
    tasks=computed, natural_completion_date=natural_completion, target_completion_date=target_completion_date,
    days_ahead_or_behind_target=days_ahead_or_behind, warnings=warnings,
  )