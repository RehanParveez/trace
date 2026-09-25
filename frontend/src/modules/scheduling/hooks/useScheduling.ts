import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { schedulingApi } from "../api/scheduling.api";

export const schedulingKeys = {
  all: ["scheduling"] as const,
  schedule: (projectId: string) => [...schedulingKeys.all, "schedule", projectId] as const,
};

export function useProjectSchedule(projectId: string) {
  return useQuery({ queryKey: schedulingKeys.schedule(projectId), queryFn: () => schedulingApi.getSchedule(projectId), enabled: Boolean(projectId) });
}

function invalidate(qc: ReturnType<typeof useQueryClient>, projectId: string) {
  void qc.invalidateQueries({ queryKey: schedulingKeys.schedule(projectId) });
}

export function useCreateTask(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: Parameters<typeof schedulingApi.createTask>[1]) => schedulingApi.createTask(projectId, payload),
    onSuccess: () => invalidate(qc, projectId),
  });
}

export function useUpdateTask(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ taskId, payload }: { taskId: string; payload: Record<string, unknown> }) => schedulingApi.updateTask(taskId, payload),
    onSuccess: () => invalidate(qc, projectId),
  });
}

export function useDeleteTask(projectId: string) {
  const qc = useQueryClient();
  return useMutation({ mutationFn: (taskId: string) => schedulingApi.deleteTask(taskId), onSuccess: () => invalidate(qc, projectId) });
}

export function useAddPredecessor(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ taskId, predecessorTaskId }: { taskId: string; predecessorTaskId: string }) =>
      schedulingApi.addPredecessor(taskId, predecessorTaskId),
    onSuccess: () => invalidate(qc, projectId),
  });
}

export function useRemovePredecessor(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ taskId, predecessorTaskId }: { taskId: string; predecessorTaskId: string }) =>
      schedulingApi.removePredecessor(taskId, predecessorTaskId),
    onSuccess: () => invalidate(qc, projectId),
  });
}

export function useUpdateScheduleSettings(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (targetCompletionDate: string | null) => schedulingApi.updateSettings(projectId, targetCompletionDate),
    onSuccess: () => invalidate(qc, projectId),
  });
}