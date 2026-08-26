import {useMutation, useQuery, useQueryClient,
} from "@tanstack/react-query";
import { identityApi } from "../api/identity.api";
import { useAuthStore } from "../store/auth.store";
import type {ChangePasswordPayload, ForgotPasswordPayload, LoginPayload, RegisterPayload, ResendVerificationPayload, ResetPasswordPayload, VerifyEmailPayload,
} from "../types/identity.types";
import { identityStorage } from "../utils/identity.storage";

export const identityKeys = {
  all: ["identity"] as const,
  me: () => ["identity", "me"] as const,
};

export function useCurrentUser() {
  const setUser = useAuthStore(
    (state) => state.setUser,
  );

  const setHydrating = useAuthStore(
    (state) => state.setHydrating,
  );

  const hasSession =
    identityStorage.hasSession();

  return useQuery({
    queryKey: identityKeys.me(),

    queryFn: async () => {
      try {
        const response =
          await identityApi.me();

        setUser(response.user);

        return response.user;
      } finally {
        setHydrating(false);
      }
    },

    enabled: hasSession,

    retry: false,

    staleTime: 5 * 60 * 1000,
  });
}

export function useLogin() {
  const queryClient =
    useQueryClient();

  const setUser = useAuthStore(
    (state) => state.setUser,
  );

  return useMutation({
    mutationFn: (
      payload: LoginPayload,
    ) => identityApi.login(payload),

    onSuccess: (response) => {
      identityStorage.setTokens(
        response.tokens.access_token,
        response.tokens.refresh_token,
      );

      setUser(response.user);

      queryClient.setQueryData(
        identityKeys.me(),
        response.user,
      );
    },
  });
}

export function useRegister() {
  return useMutation({
    mutationFn: (
      payload: RegisterPayload,
    ) => identityApi.register(payload),
  });
}

export function useForgotPassword() {
  return useMutation({
    mutationFn: (
      payload: ForgotPasswordPayload,
    ) =>
      identityApi.forgotPassword(payload),
  });
}

export function useResetPassword() {
  return useMutation({
    mutationFn: (
      payload: ResetPasswordPayload,
    ) =>
      identityApi.resetPassword(payload),
  });
}

export function useVerifyEmail() {
  return useMutation({
    mutationFn: (
      payload: VerifyEmailPayload,
    ) =>
      identityApi.verifyEmail(payload),
  });
}

export function useResendVerification() {
  return useMutation({
    mutationFn: (
      payload: ResendVerificationPayload,
    ) =>
      identityApi.resendVerification(
        payload,
      ),
  });
}

export function useChangePassword() {
  return useMutation({
    mutationFn: (
      payload: ChangePasswordPayload,
    ) =>
      identityApi.changePassword(payload),
  });
}

export function useLogout() {
  const queryClient =
    useQueryClient();

  const clearSession =
    useAuthStore(
      (state) => state.clearSession,
    );

  return useMutation({
    mutationFn: async () => {
      const refreshToken =
        identityStorage.getRefreshToken();

      if (!refreshToken) {
        return;
      }

      return identityApi.logout(
        refreshToken,
      );
    },

    onSettled: () => {
      clearSession();

      queryClient.clear();
    },
  });
}

export function useLogoutAll() {
  const queryClient =
    useQueryClient();

  const clearSession =
    useAuthStore(
      (state) => state.clearSession,
    );

  return useMutation({
    mutationFn: () =>
      identityApi.logoutAll(),

    onSettled: () => {
      clearSession();

      queryClient.clear();
    },
  });
}