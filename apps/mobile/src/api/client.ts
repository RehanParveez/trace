import type {ApiErrorBody, AuthTokens, AuthUser, CurrentUserResponse, LoginResponse, RegisterPayload, MessageResponse, RegistrationResponse,
} from "./types";
import { clearTokens, loadTokens, saveTokens } from "../auth/tokenStore";

const API_BASE_URL = process.env.EXPO_PUBLIC_API_BASE_URL?.replace(/\/+$/, "");

let accessToken: string | null = null;
let refreshInFlight: Promise<string | null> | null = null;

function getBaseUrl(): string {
  if (!API_BASE_URL) {
    throw new Error("Set EXPO_PUBLIC_API_BASE_URL in apps/mobile/.env.local");
  }
  return API_BASE_URL;
}

async function readBody<T>(response: Response): Promise<T> {
  const text = await response.text();

  let body: unknown;
  try {
    body = text ? JSON.parse(text) : undefined;
  } catch {
    body = { detail: text };
  }

  if (!response.ok) {
    const errorBody = body as ApiErrorBody | undefined;
    const detail = errorBody?.detail;
    const message =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail.map((item) => item.msg ?? "Invalid request").join(", ")
          : errorBody?.message;

    throw new Error(message ?? `Request failed (${response.status})`);
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

  return fetch(`${getBaseUrl()}${path}`, { ...init, headers });
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