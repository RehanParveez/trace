export type ScheduleTaskStatus = "NOT_STARTED" | "IN_PROGRESS" | "COMPLETE";

export interface ScheduleTask {
  id: string;
  name: string;
  description: string | null;
  planned_start_date: string | null;
  planned_duration_days: number;
  is_milestone_marker: boolean;
  actual_start_date: string | null;
  actual_end_date: string | null;
  percent_complete: number | string;
  status: ScheduleTaskStatus;
  sort_order: number;
}

export interface ScheduleTaskComputed extends ScheduleTask {
  predecessor_task_ids: string[];
  is_computable: boolean;
  earliest_start: string | null;
  earliest_finish: string | null;
  latest_start: string | null;
  latest_finish: string | null;
  total_float_days: number | null;
  is_critical: boolean;
}

export interface ProjectSchedule {
  project_id: string;
  target_completion_date: string | null;
  natural_completion_date: string | null;
  days_ahead_or_behind_target: number | null;
  warnings: string[];
  tasks: ScheduleTaskComputed[];
}