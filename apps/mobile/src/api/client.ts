import type {ApiErrorBody, AuthTokens, AuthUser, CurrentUserResponse, LoginResponse, RegisterPayload, MessageResponse, RegistrationResponse, InvitationPreview, ChangePasswordPayload
} from "./types";
import { clearTokens, loadTokens, saveTokens } from "../auth/tokenStore";
import { fetch as expoFetch } from "expo/fetch";

const API_BASE_URL = process.env.EXPO_PUBLIC_API_BASE_URL?.replace(/\/+$/, "")

let accessToken: string | null = null;
let refreshInFlight: Promise<string | null> | null = null;

function getBaseUrl(): string {
  if (!API_BASE_URL) {
    throw new Error("Set EXPO_PUBLIC_API_BASE_URL in apps/mobile/.env.local");
  }
  return API_BASE_URL;
}

export class ApiError extends Error {
  status: number;
  code: string | null;

  constructor(message: string, status: number, code: string | null = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

export function errorCode(err: unknown): string | null {
  return err instanceof ApiError ? err.code : null;
}

async function readBody<T>(response: Response): Promise<T> {
  const text = await response.text();

  let body: unknown;
  try {
    body = text ? JSON.parse(text) : undefined;
  } catch {
    body = undefined;
  }

  if (!response.ok) {
    const record =
      body && typeof body === "object"
        ? (body as Record<string, unknown>)
        : undefined;
    const detail = record?.detail;
    let message: string | undefined;

    if (typeof detail === "string") {
      message = detail;
    } else if (Array.isArray(detail)) {
      message = detail
        .map((entry) => {
          if (!entry || typeof entry !== "object") return "";
          const item = entry as Record<string, unknown>;
          const msg = typeof item.msg === "string" ? item.msg : "Invalid request";
          const loc = Array.isArray(item.loc)
            ? item.loc.filter((part) => part !== "body").join(".")
            : "";
          return loc ? `${loc}: ${msg}` : msg;
        })
        .filter(Boolean)
        .join(", ");
    } else if (detail && typeof detail === "object") {
      const detailRecord = detail as Record<string, unknown>;
      message =
        (typeof detailRecord.message === "string" && detailRecord.message) ||
        (typeof detailRecord.msg === "string" && detailRecord.msg) ||
        undefined;
    }

    let code: string | null = null;
    const errorObject = record?.error;
    if (errorObject && typeof errorObject === "object") {
      const errorRecord = errorObject as Record<string, unknown>;
      if (!message && typeof errorRecord.message === "string") {
        message = errorRecord.message;
      }
      if (typeof errorRecord.code === "string") {
        code = errorRecord.code;
      }
    }

    if (!message && typeof record?.message === "string") {
      message = record.message;
    }
    if (!message && typeof record?.error === "string") {
      message = record.error;
    }

    throw new ApiError(
      message || text.trim() || `Request failed (${response.status})`,
      response.status,
      code,
    );
  }

  return body as T;
}

async function rawRequest(
  path: string,
  init: RequestInit = {},
  token: string | null = null,
): Promise<Response> {
  const headers = new Headers(init.headers);

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  if (typeof init.body === "string" && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const isFormData =
    typeof FormData !== "undefined" && init.body instanceof FormData;
  const requestFetch = isFormData ? expoFetch : fetch;

  return requestFetch(`${getBaseUrl()}${path}`, { ...init, headers });
}

async function refreshAccessToken(): Promise<string | null> {
  if (!refreshInFlight) {
    refreshInFlight = (async () => {
      const saved = await loadTokens();
      if (!saved?.refresh_token) {
        return null;
      }

      try {
        const response = await rawRequest("/auth/refresh", {
          method: "POST",
          body: JSON.stringify({ refresh_token: saved.refresh_token }),
        });
        const tokens = await readBody<AuthTokens>(response);

        await saveTokens(tokens);
        accessToken = tokens.access_token;
        return tokens.access_token;
      } catch {
        await clearTokens();
        accessToken = null;
        return null;
      }
    })().finally(() => {
      refreshInFlight = null;
    });
  }

  return refreshInFlight;
}

export async function authenticatedRequest<T>(
  path: string,
  init: RequestInit = {},
  mayRetry = true,
): Promise<T> {
  const response = await rawRequest(path, init, accessToken);

  if (response.status === 401 && mayRetry) {
    const nextToken = await refreshAccessToken();
    if (nextToken) {
      return authenticatedRequest<T>(path, init, false);
    }
  }

  return readBody<T>(response);
}

export async function authenticatedResponse(
  path: string,
  init: RequestInit = {},
): Promise<Response> {
  let response = await rawRequest(path, init, accessToken);

  if (response.status === 401) {
    const nextToken = await refreshAccessToken();
    if (nextToken) {
      response = await rawRequest(path, init, nextToken);
    }
  }

  if (!response.ok) {
    await readBody<unknown>(response.clone());
  }

  return response;
}

export async function signIn(email: string, password: string): Promise<AuthUser> {
  const response = await rawRequest("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email: email.trim(), password }),
  });
  const result = await readBody<LoginResponse>(response);

  await saveTokens(result.tokens);
  accessToken = result.tokens.access_token;
  return result.user;
}

export async function restoreSession(): Promise<AuthUser | null> {
  const saved = await loadTokens();
  if (!saved) {
    return null;
  }

  accessToken = saved.access_token;
  const result = await authenticatedRequest<CurrentUserResponse>("/auth/me");
  return result.user;
}

export async function signOut(): Promise<void> {
  const saved = await loadTokens();

  try {
    if (saved?.refresh_token) {
      await rawRequest("/auth/logout", {
        method: "POST",
        body: JSON.stringify({ refresh_token: saved.refresh_token }),
      });
    }
  } finally {
    accessToken = null;
    await clearTokens();
  }
}

async function publicRequest<T>(
  path: string,
  body: unknown,
): Promise<T> {
  const response = await rawRequest(path, {
    method: "POST",
    body: JSON.stringify(body),
  });

  return readBody<T>(response);
}

export function register(payload: RegisterPayload) {
  return publicRequest<RegistrationResponse>("/auth/register", {
    ...payload,
    first_name: payload.first_name.trim(),
    last_name: payload.last_name.trim(),
    email: payload.email.trim().toLowerCase(),
  });
}

export function verifyEmail(token: string) {
  return publicRequest<MessageResponse>("/auth/verify-email", { token });
}

export async function previewInvitation(
  token: string,
): Promise<InvitationPreview> {
  const response = await rawRequest(
    `/auth/invitations/${encodeURIComponent(token)}/preview`,
  );
  return readBody<InvitationPreview>(response);
}

export async function changePassword(
  payload: ChangePasswordPayload,
): Promise<MessageResponse> {
  const result = await authenticatedRequest<MessageResponse>(
    "/auth/change-password",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );

  accessToken = null;
  await clearTokens();
  return result;
}

export async function signOutAll(): Promise<MessageResponse> {
  try {
    return await authenticatedRequest<MessageResponse>(
      "/auth/logout-all",
      { method: "POST" },
    );
  } finally {
    accessToken = null;
    await clearTokens();
  }
}

export function resendVerification(email: string) {
  return publicRequest<MessageResponse>("/auth/resend-verification", {
    email: email.trim().toLowerCase(),
  });
}

export function forgotPassword(email: string) {
  return publicRequest<MessageResponse>("/auth/forgot-password", {
    email: email.trim().toLowerCase(),
  });
}

export function resetPassword(
  token: string,
  password: string,
  password_confirmation: string,
) {
  return publicRequest<MessageResponse>("/auth/reset-password", {
    token,
    password,
    password_confirmation,
  });
}