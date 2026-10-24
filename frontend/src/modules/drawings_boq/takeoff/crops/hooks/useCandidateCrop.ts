import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { takeoffKeys } from "../../hooks/useTakeoff";
import { cropsApi } from "../api/crops.api";

export function useCandidateCrop(candidateId: string, key: string, size: number, enabled: boolean) {
  const q = useQuery({
    queryKey: [...takeoffKeys.all, "crop", key, size],
    queryFn: () => cropsApi.candidate(candidateId, size),
    enabled,
    staleTime: 5 * 60_000,
    gcTime: 5 * 60_000,
    retry: false,
  });
  const [url, setUrl] = useState<string | null>(null);
  useEffect(() => {
    if (!q.data) { setUrl(null); return; }
    const made = URL.createObjectURL(q.data);
    setUrl(made);
    return () => URL.revokeObjectURL(made);
  }, [q.data]);
  return { url, loading: enabled && q.isLoading, failed: q.isError, retry: () => void q.refetch() };
}
