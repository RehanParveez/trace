import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { pricingKeys } from "../../hooks";
import { schedulesApi, type RowQuery } from "../api/schedules.api";
import type {BulkPayload, CompareMatch, EscalationFromComparePayload, ImportRow, ImportStatus, PublishPayload, RateImport, RefreshPayload, ReparsePayload, RowUpdatePayload, UploadPayload,
} from "../types/schedules.types";

const PAGE = 80;

export const scheduleKeys = {
  all: ["rate-schedules"] as const,
  list: (status: ImportStatus | null) => [...scheduleKeys.all, "list", status] as const,
  listAll: () => [...scheduleKeys.all, "list"] as const,
  one: (id: string) => [...scheduleKeys.all, "one", id] as const,
  rows: (id: string, q: RowQuery) => [...scheduleKeys.all, "rows", id, q] as const,
  rowsAll: (id: string) => [...scheduleKeys.all, "rows", id] as const,
  chapters: (id: string) => [...scheduleKeys.all, "chapters", id] as const,
  readiness: (id: string, includeUnmapped: boolean) => [...scheduleKeys.all, "readiness", id, includeUnmapped] as const,
  compare: (a: string, b: string, m: CompareMatch) => [...scheduleKeys.all, "compare", a, b, m] as const,
  history: (book: string, code: string, unit: string) => [...scheduleKeys.all, "history", book, code, unit] as const,
  gaps: (versionId: string) => [...scheduleKeys.all, "gaps", versionId] as const,
};

const BUSY: ImportStatus[] = ["UPLOADED", "PARSING"];

export function useRateImports(status: ImportStatus | null = null) {
  const query = useInfiniteQuery({
    queryKey: scheduleKeys.list(status),
    queryFn: ({ pageParam }) => schedulesApi.list({ status, limit: 50, after: pageParam }),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (last) => last.nextCursor ?? undefined,
    refetchInterval: (q) => (q.state.data?.pages.some((p) => p.items.some((i) => BUSY.includes(i.status))) ? 4000 : false),
  });
  return { ...query, imports: (query.data?.pages.flatMap((p) => p.items) ?? []) as RateImport[] };
}

export function useRateImport(id: string | undefined) {
  return useQuery({
    queryKey: scheduleKeys.one(id ?? ""),
    queryFn: () => schedulesApi.get(id as string),
    enabled: Boolean(id),
    refetchInterval: (q) => (q.state.data && BUSY.includes(q.state.data.status) ? 3000 : false),
  });
}

export function useImportRows(id: string, query: RowQuery, enabled: boolean) {
  const result = useInfiniteQuery({
    queryKey: scheduleKeys.rows(id, query),
    queryFn: ({ pageParam }) => schedulesApi.rows(id, query, pageParam ?? null, PAGE),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (last) => last.nextCursor ?? undefined,
    enabled,
  });
  return { ...result, rows: (result.data?.pages.flatMap((p) => p.items) ?? []) as ImportRow[] };
}

export function useImportChapters(id: string, enabled: boolean) {
  return useQuery({ queryKey: scheduleKeys.chapters(id), queryFn: () => schedulesApi.chapters(id), enabled });
}

export function useReadiness(id: string, includeUnmapped: boolean, enabled: boolean) {
  return useQuery({ queryKey: scheduleKeys.readiness(id, includeUnmapped), queryFn: () => schedulesApi.readiness(id, includeUnmapped), enabled, staleTime: 0 });
}

function useRefreshImport(id: string) {
  const qc = useQueryClient();
  return () => {
    void qc.invalidateQueries({ queryKey: scheduleKeys.rowsAll(id) });
    void qc.invalidateQueries({ queryKey: scheduleKeys.one(id) });
    void qc.invalidateQueries({ queryKey: scheduleKeys.chapters(id) });
    void qc.invalidateQueries({ queryKey: [...scheduleKeys.all, "readiness", id] });
  };
}

export function useUploadSchedule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: UploadPayload) => schedulesApi.upload(payload),
    onSuccess: () => void qc.invalidateQueries({ queryKey: scheduleKeys.listAll() }),
  });
}

export function useDeleteImport() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => schedulesApi.remove(id),
    onSuccess: () => void qc.invalidateQueries({ queryKey: scheduleKeys.listAll() }),
  });
}

export function useReparseImport(id: string) {
  const refresh = useRefreshImport(id);
  return useMutation({ mutationFn: (payload: ReparsePayload) => schedulesApi.reparse(id, payload), onSuccess: refresh });
}

export function useUpdateImportRow(id: string) {
  const refresh = useRefreshImport(id);
  return useMutation({ mutationFn: (v: { rowId: string; payload: RowUpdatePayload }) => schedulesApi.updateRow(id, v.rowId, v.payload), onSuccess: refresh });
}

export function useBulkRows(id: string) {
  const refresh = useRefreshImport(id);
  return useMutation({ mutationFn: (payload: BulkPayload) => schedulesApi.bulk(id, payload), onSuccess: refresh });
}

export function useRefreshSuggestions(id: string) {
  const refresh = useRefreshImport(id);
  return useMutation({ mutationFn: () => schedulesApi.suggest(id), onSuccess: refresh });
}

export function usePublishImport(id: string) {
  const qc = useQueryClient();
  const refresh = useRefreshImport(id);
  return useMutation({
    mutationFn: (payload: PublishPayload) => schedulesApi.publish(id, payload),
    onSuccess: () => {
      refresh();
      void qc.invalidateQueries({ queryKey: pricingKeys.booksAll() });
      void qc.invalidateQueries({ queryKey: scheduleKeys.listAll() });
    },
  });
}

export function useCompareBooks(bookId: string, otherId: string, matchOn: CompareMatch) {
  return useQuery({ queryKey: scheduleKeys.compare(bookId, otherId, matchOn), queryFn: () => schedulesApi.compare(bookId, otherId, matchOn), enabled: Boolean(otherId) });
}

export function useRateHistory(bookId: string, code: string, unit: string) {
  return useQuery({ queryKey: scheduleKeys.history(bookId, code, unit), queryFn: () => schedulesApi.history(bookId, code, unit), enabled: code.trim().length > 0 });
}

export function useRefreshBook(bookId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: RefreshPayload) => schedulesApi.refresh(bookId, payload),
    onSuccess: (result) => {
      if (result.applied) {
        void qc.invalidateQueries({ queryKey: pricingKeys.itemsAll(bookId) });
        void qc.invalidateQueries({ queryKey: pricingKeys.analyses(bookId) });
        void qc.invalidateQueries({ queryKey: pricingKeys.book(bookId) });
      }
    },
  });
}

export function useEscalationsFromCompare(bookId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: EscalationFromComparePayload) => schedulesApi.escalationsFromCompare(bookId, payload),
    onSuccess: (result) => {
      if (result.applied && result.created > 0) {
        void qc.invalidateQueries({ queryKey: pricingKeys.escalations(bookId) });
        void qc.invalidateQueries({ queryKey: pricingKeys.book(bookId) });
        void qc.invalidateQueries({ queryKey: pricingKeys.booksAll() });
      }
    },
  });
}

export function useRateGaps(versionId: string, enabled: boolean) {
  return useQuery({ queryKey: scheduleKeys.gaps(versionId), queryFn: () => schedulesApi.rateGaps(versionId), enabled });
}
