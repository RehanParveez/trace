import { apiClient } from "../../../shared/api/client";
import type { ProjectSchedule } from "../types/scheduling.types";

export const schedulingApi = {
  async getSchedule(projectId: string): Promise<ProjectSchedule> {
    return (await apiClient.get<ProjectSchedule>(`/scheduling/projects/${projectId}/schedule`)).data;
  },
  async createTask(projectId: string, payload: {
    name: string; description?: string | null; planned_start_date?: string | null;
    planned_duration_days: number; is_milestone_marker?: boolean; predecessor_task_ids?: string[];
  }): Promise<void> {
    await apiClient.post(`/scheduling/projects/${projectId}/tasks`, payload);
  },
  async updateTask(taskId: string, payload: Record<string, unknown>): Promise<void> {
    await apiClient.patch(`/scheduling/tasks/${taskId}`, payload);
  },
  async deleteTask(taskId: string): Promise<void> {
    await apiClient.delete(`/scheduling/tasks/${taskId}`);
  },
  async addPredecessor(taskId: string, predecessorTaskId: string): Promise<void> {
    await apiClient.post(`/scheduling/tasks/${taskId}/predecessors`, { predecessor_task_id: predecessorTaskId });
  },
  async removePredecessor(taskId: string, predecessorTaskId: string): Promise<void> {
    await apiClient.delete(`/scheduling/tasks/${taskId}/predecessors/${predecessorTaskId}`);
  },
  async updateSettings(projectId: string, targetCompletionDate: string | null): Promise<void> {
    await apiClient.patch(`/scheduling/projects/${projectId}/settings`, { target_completion_date: targetCompletionDate });
  },
};