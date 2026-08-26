import { apiClient } from "../../../shared/api/client";
import type {ChangePasswordPayload, CurrentUserResponse, ForgotPasswordPayload, LoginPayload, LoginResponse, MessageResponse, RegisterPayload, RegistrationResponse, ResendVerificationPayload, ResetPasswordPayload,
  TokenResponse, VerifyEmailPayload,
} from "../types/identity.types";

export const identityApi = {
  async login(
    payload: LoginPayload,
  ): Promise<LoginResponse> {
    const { data } =
      await apiClient.post<LoginResponse>(
        "/auth/login",
        payload,
      );

    return data;
  },

  async refresh(
    refreshToken: string,
  ): Promise<TokenResponse> {
    const { data } =
      await apiClient.post<TokenResponse>(
        "/auth/refresh",
        {
          refresh_token: refreshToken,
        },
      );

    return data;
  },

  async logout(
    refreshToken: string,
  ): Promise<MessageResponse> {
    const { data } =
      await apiClient.post<MessageResponse>(
        "/auth/logout",
        {
          refresh_token: refreshToken,
        },
      );

    return data;
  },

  async logoutAll(): Promise<MessageResponse> {
    const { data } =
      await apiClient.post<MessageResponse>(
        "/auth/logout-all",
      );

    return data;
  },

  async me(): Promise<CurrentUserResponse> {
    const { data } =
      await apiClient.get<CurrentUserResponse>(
        "/auth/me",
      );

    return data;
  },

  async register(
    payload: RegisterPayload,
  ): Promise<RegistrationResponse> {
    const { data } =
      await apiClient.post<RegistrationResponse>(
        "/auth/register",
        payload,
      );

    return data;
  },

  async forgotPassword(
    payload: ForgotPasswordPayload,
  ): Promise<MessageResponse> {
    const { data } =
      await apiClient.post<MessageResponse>(
        "/auth/forgot-password",
        payload,
      );

    return data;
  },

  async resetPassword(
    payload: ResetPasswordPayload,
  ): Promise<MessageResponse> {
    const { data } =
      await apiClient.post<MessageResponse>(
        "/auth/reset-password",
        payload,
      );

    return data;
  },

  async verifyEmail(
    payload: VerifyEmailPayload,
  ): Promise<MessageResponse> {
    const { data } =
      await apiClient.post<MessageResponse>(
        "/auth/verify-email",
        payload,
      );

    return data;
  },

  async resendVerification(
    payload: ResendVerificationPayload,
  ): Promise<MessageResponse> {
    const { data } =
      await apiClient.post<MessageResponse>(
        "/auth/resend-verification",
        payload,
      );

    return data;
  },

  async changePassword(
    payload: ChangePasswordPayload,
  ): Promise<MessageResponse> {
    const { data } =
      await apiClient.post<MessageResponse>(
        "/auth/change-password",
        payload,
      );

    return data;
  },
};