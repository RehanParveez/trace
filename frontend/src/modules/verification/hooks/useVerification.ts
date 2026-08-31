import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { verificationApi } from "../api/verification.api";
import type {PhotoBOQLinkCreateRequest, ProgressClaim, ProgressClaimCreateRequest, ProgressClaimReviewRequest, ProgressClaimStatus, ProgressClaimUpdateRequest,
} from "../types/verification.types";

export const verificationKeys = {
  all: ["verification"] as const,
  claims: (projectId?: string, status?: ProgressClaimStatus) =>
    [...verificationKeys.all, "claims", projectId ?? "all", status ?? "any"] as const,
  claim: (claimId: string) => [...verificationKeys.all, "claim", claimId] as const,
  links: (claimId: string) => [...verificationKeys.all, "links", claimId] as const,
};

export function useProgressClaims(projectId?: string, status?: ProgressClaimStatus) {
  return useQuery({
    queryKey: verificationKeys.claims(projectId, status),
    queryFn: () => verificationApi.listClaims({ projectId, status }),
  });
}

export function useProgressClaim(claimId: string | undefined) {
  return useQuery({
    queryKey: verificationKeys.claim(claimId ?? ""),
    queryFn: () => verificationApi.getClaim(claimId!),
    enabled: Boolean(claimId),
  });
}

function invalidateClaimLists(queryClient: ReturnType<typeof useQueryClient>) {
  void queryClient.invalidateQueries({
    queryKey: verificationKeys.all,
    predicate: (query) => query.queryKey[1] === "claims",
  });
}

export function useCreateProgressClaim() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: ProgressClaimCreateRequest) => verificationApi.createClaim(payload),
    onSuccess: () => invalidateClaimLists(queryClient),
  });
}

function onClaimMutated(queryClient: ReturnType<typeof useQueryClient>, claim: ProgressClaim) {
  queryClient.setQueryData(verificationKeys.claim(claim.id), claim);
  invalidateClaimLists(queryClient);
}

export function useUpdateProgressClaim() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ claimId, payload }: { claimId: string; payload: ProgressClaimUpdateRequest }) =>
      verificationApi.updateClaim(claimId, payload),
    onSuccess: (claim) => onClaimMutated(queryClient, claim),
  });
}

export function useSubmitProgressClaim() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (claimId: string) => verificationApi.submitClaim(claimId),
    onSuccess: (claim) => onClaimMutated(queryClient, claim),
  });
}

export function useApproveProgressClaim() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ claimId, payload }: { claimId: string; payload: ProgressClaimReviewRequest }) =>
      verificationApi.approveClaim(claimId, payload),
    onSuccess: (claim) => onClaimMutated(queryClient, claim),
  });
}

export function useRejectProgressClaim() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ claimId, payload }: { claimId: string; payload: ProgressClaimReviewRequest }) =>
      verificationApi.rejectClaim(claimId, payload),
    onSuccess: (claim) => onClaimMutated(queryClient, claim),
  });
}

export function usePhotoBOQLinks(claimId: string | undefined) {
  return useQuery({
    queryKey: verificationKeys.links(claimId ?? ""),
    queryFn: () => verificationApi.listPhotoBOQLinks(claimId!),
    enabled: Boolean(claimId),
  });
}

export function useCreatePhotoBOQLink(claimId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: PhotoBOQLinkCreateRequest) => verificationApi.createPhotoBOQLink(payload),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: verificationKeys.links(claimId) }),
  });
}

export function useDeletePhotoBOQLink(claimId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (linkId: string) => verificationApi.deletePhotoBOQLink(linkId),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: verificationKeys.links(claimId) }),
  });
}