import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { pricingApi } from "../api/pricing.api";
import { drawingsBoqKeys } from "../../hooks";
import type {AnalysisCreatePayload, AnalysisUpdatePayload, DiffOptions, EscalationCreatePayload, OverrideCreatePayload, PriceVersionPayload, RateBook, RateBookCreatePayload, RateBookFilters, 
  RateBookUpdatePayload, RateItemFilters, RateItemInput, RateItemUpdatePayload,
} from "../types/pricing.types";

const PAGE_SIZE = 100;

export const pricingKeys = {
  all: ["pricing"] as const,
  books: (filters: RateBookFilters) => [...pricingKeys.all, "books", filters] as const,
  booksAll: () => [...pricingKeys.all, "books"] as const,
  book: (id: string) => [...pricingKeys.all, "book", id] as const,
  items: (bookId: string, filters: RateItemFilters) => [...pricingKeys.all, "items", bookId, filters] as const,
  itemsAll: (bookId: string) => [...pricingKeys.all, "items", bookId] as const,
  escalations: (bookId: string) => [...pricingKeys.all, "escalations", bookId] as const,
  analyses: (bookId: string) => [...pricingKeys.all, "analyses", bookId] as const,
  breakdown: (analysisId: string) => [...pricingKeys.all, "breakdown", analysisId] as const,
  overrides: (projectId: string, includeRevoked: boolean) =>
    [...pricingKeys.all, "overrides", projectId, includeRevoked] as const,
  overridesAll: (projectId: string) => [...pricingKeys.all, "overrides", projectId] as const,
  summary: (versionId: string) => [...pricingKeys.all, "summary", versionId] as const,
  explain: (itemId: string, asOf: string) => [...pricingKeys.all, "explain", itemId, asOf] as const,
  diff: (a: string, b: string, options: DiffOptions) => [...pricingKeys.all, "diff", a, b, options] as const,
};

export function useRateBooks(filters: RateBookFilters = {}) {
  const query = useInfiniteQuery({
    queryKey: pricingKeys.books(filters),
    queryFn: ({ pageParam }) => pricingApi.listRateBooks({ ...filters, limit: PAGE_SIZE, after: pageParam }),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (last) => last.nextCursor ?? undefined,
  });
  return {
    ...query,
    books: (query.data?.pages.flatMap((page) => page.items) ?? []) as RateBook[],
  };
}

export function useRateBook(id: string | undefined) {
  return useQuery({
    queryKey: pricingKeys.book(id ?? ""),
    queryFn: () => pricingApi.getRateBook(id as string),
    enabled: Boolean(id),
  });
}

function invalidateBooks(qc: ReturnType<typeof useQueryClient>, id?: string) {
  void qc.invalidateQueries({ queryKey: pricingKeys.booksAll() });
  if (id) void qc.invalidateQueries({ queryKey: pricingKeys.book(id) });
}

export function useCreateRateBook() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: RateBookCreatePayload) => pricingApi.createRateBook(payload),
    onSuccess: () => invalidateBooks(qc),
  });
}

export function useUpdateRateBook(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: RateBookUpdatePayload) => pricingApi.updateRateBook(id, payload),
    onSuccess: () => invalidateBooks(qc, id),
  });
}

export function useDeleteRateBook() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => pricingApi.deleteRateBook(id),
    onSuccess: () => invalidateBooks(qc),
  });
}

export function usePublishRateBook() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => pricingApi.publishRateBook(id),
    onSuccess: (_book, id) => invalidateBooks(qc, id),
  });
}

export function useNewRateBookVersion() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => pricingApi.newRateBookVersion(id),
    onSuccess: () => invalidateBooks(qc),
  });
}

export function useArchiveRateBook() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => pricingApi.archiveRateBook(id),
    onSuccess: (_book, id) => invalidateBooks(qc, id),
  });
}

export function useRateItems(bookId: string | undefined, filters: RateItemFilters = {}) {
  const query = useInfiniteQuery({
    queryKey: pricingKeys.items(bookId ?? "", filters),
    queryFn: ({ pageParam }) =>
      pricingApi.listRateItems(bookId as string, { ...filters, limit: PAGE_SIZE, after: pageParam }),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (last) => last.nextCursor ?? undefined,
    enabled: Boolean(bookId),
  });
  return {
    ...query,
    items: query.data?.pages.flatMap((page) => page.items) ?? [],
  };
}

function invalidateItems(qc: ReturnType<typeof useQueryClient>, bookId: string) {
  void qc.invalidateQueries({ queryKey: pricingKeys.itemsAll(bookId) });
  void qc.invalidateQueries({ queryKey: pricingKeys.book(bookId) });
  void qc.invalidateQueries({ queryKey: pricingKeys.booksAll() });
}

export function useAddRateItem(bookId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: RateItemInput) => pricingApi.addRateItem(bookId, payload),
    onSuccess: () => invalidateItems(qc, bookId),
  });
}

export function useBulkUpsertRateItems(bookId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (items: RateItemInput[]) => pricingApi.bulkUpsertRateItems(bookId, items),
    onSuccess: () => invalidateItems(qc, bookId),
  });
}

export function useImportRateItemsCsv(bookId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => pricingApi.importRateItemsCsv(bookId, file),
    onSuccess: () => invalidateItems(qc, bookId),
  });
}

export function useUpdateRateItem(bookId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ itemId, payload }: { itemId: string; payload: RateItemUpdatePayload }) =>
      pricingApi.updateRateItem(itemId, payload),
    onSuccess: () => invalidateItems(qc, bookId),
  });
}

export function useDeleteRateItem(bookId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (itemId: string) => pricingApi.deleteRateItem(itemId),
    onSuccess: () => invalidateItems(qc, bookId),
  });
}

export function useEscalations(bookId: string | undefined) {
  return useQuery({
    queryKey: pricingKeys.escalations(bookId ?? ""),
    queryFn: () => pricingApi.listEscalations(bookId as string),
    enabled: Boolean(bookId),
  });
}

function invalidateEscalations(qc: ReturnType<typeof useQueryClient>, bookId: string) {
  void qc.invalidateQueries({ queryKey: pricingKeys.escalations(bookId) });
  void qc.invalidateQueries({ queryKey: pricingKeys.book(bookId) });
  void qc.invalidateQueries({ queryKey: pricingKeys.booksAll() });
}

export function useAddEscalation(bookId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: EscalationCreatePayload) => pricingApi.addEscalation(bookId, payload),
    onSuccess: () => invalidateEscalations(qc, bookId),
  });
}

export function useDeleteEscalation(bookId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (escalationId: string) => pricingApi.deleteEscalation(escalationId),
    onSuccess: () => invalidateEscalations(qc, bookId),
  });
}

export function useAnalyses(bookId: string | undefined) {
  return useQuery({
    queryKey: pricingKeys.analyses(bookId ?? ""),
    queryFn: () => pricingApi.listAnalyses(bookId as string),
    enabled: Boolean(bookId),
  });
}

export function useAnalysisBreakdown(analysisId: string | undefined) {
  return useQuery({
    queryKey: pricingKeys.breakdown(analysisId ?? ""),
    queryFn: () => pricingApi.getAnalysisBreakdown(analysisId as string),
    enabled: Boolean(analysisId),
  });
}

function invalidateAnalyses(qc: ReturnType<typeof useQueryClient>, bookId: string, analysisId?: string) {
  void qc.invalidateQueries({ queryKey: pricingKeys.analyses(bookId) });
  void qc.invalidateQueries({ queryKey: pricingKeys.book(bookId) });
  void qc.invalidateQueries({ queryKey: pricingKeys.booksAll() });
  if (analysisId) void qc.invalidateQueries({ queryKey: pricingKeys.breakdown(analysisId) });
}

export function useCreateAnalysis(bookId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: AnalysisCreatePayload) => pricingApi.createAnalysis(bookId, payload),
    onSuccess: () => invalidateAnalyses(qc, bookId),
  });
}

export function useUpdateAnalysis(bookId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ analysisId, payload }: { analysisId: string; payload: AnalysisUpdatePayload }) =>
      pricingApi.updateAnalysis(analysisId, payload),
    onSuccess: (_analysis, vars) => invalidateAnalyses(qc, bookId, vars.analysisId),
  });
}

export function useDeleteAnalysis(bookId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (analysisId: string) => pricingApi.deleteAnalysis(analysisId),
    onSuccess: () => invalidateAnalyses(qc, bookId),
  });
}

export function useComputeAnalysis(bookId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (analysisId: string) => pricingApi.computeAnalysis(analysisId),
    onSuccess: (_analysis, analysisId) => invalidateAnalyses(qc, bookId, analysisId),
  });
}

export function useApplyAnalysis(bookId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (analysisId: string) => pricingApi.applyAnalysis(analysisId),
    onSuccess: (_item, analysisId) => {
      invalidateAnalyses(qc, bookId, analysisId);
      invalidateItems(qc, bookId);
    },
  });
}

export function useProjectOverrides(projectId: string | undefined, includeRevoked = false) {
  const query = useInfiniteQuery({
    queryKey: pricingKeys.overrides(projectId ?? "", includeRevoked),
    queryFn: ({ pageParam }) =>
      pricingApi.listOverrides(projectId as string, {
        include_revoked: includeRevoked,
        limit: PAGE_SIZE,
        after: pageParam,
      }),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (last) => last.nextCursor ?? undefined,
    enabled: Boolean(projectId),
  });
  return {
    ...query,
    overrides: query.data?.pages.flatMap((page) => page.items) ?? [],
  };
}

export function useCreateOverride(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: OverrideCreatePayload) => pricingApi.createOverride(projectId, payload),
    onSuccess: () => void qc.invalidateQueries({ queryKey: pricingKeys.overridesAll(projectId) }),
  });
}

export function useRevokeOverride(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ overrideId, reason }: { overrideId: string; reason: string }) =>
      pricingApi.revokeOverride(overrideId, reason),
    onSuccess: () => void qc.invalidateQueries({ queryKey: pricingKeys.overridesAll(projectId) }),
  });
}

export function usePricingSummary(versionId: string | undefined) {
  return useQuery({
    queryKey: pricingKeys.summary(versionId ?? ""),
    queryFn: () => pricingApi.getPricingSummary(versionId as string),
    enabled: Boolean(versionId),
  });
}

export function usePriceVersion(projectId: string, versionId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: PriceVersionPayload) => pricingApi.priceVersion(versionId, payload),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: pricingKeys.summary(versionId) });
      void qc.invalidateQueries({ queryKey: drawingsBoqKeys.boqItems(versionId) });
      void qc.invalidateQueries({ queryKey: drawingsBoqKeys.boqSummary(versionId) });
      void qc.invalidateQueries({ queryKey: drawingsBoqKeys.boqVersions(projectId) });
      void qc.invalidateQueries({ queryKey: [...drawingsBoqKeys.all, "issues", projectId] });
    },
  });
}

export function useRateExplain(itemId: string | undefined, asOf: string, enabled = true) {
  return useQuery({
    queryKey: pricingKeys.explain(itemId ?? "", asOf),
    queryFn: () => pricingApi.explainItemRate(itemId as string, asOf || null),
    enabled: Boolean(itemId) && enabled,
  });
}

export function useVersionDiff(
  versionA: string | undefined,
  versionB: string | undefined,
  options: DiffOptions = {},
) {
  return useQuery({
    queryKey: pricingKeys.diff(versionA ?? "", versionB ?? "", options),
    queryFn: () => pricingApi.diffVersions(versionA as string, versionB as string, options),
    enabled: Boolean(versionA) && Boolean(versionB) && versionA !== versionB,
  });
}