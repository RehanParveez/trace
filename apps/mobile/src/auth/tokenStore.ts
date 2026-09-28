import * as SecureStore from "expo-secure-store";
import type { AuthTokens } from "../api/types";

const ACCESS_TOKEN_KEY = "trace.mobile.access_token";
const REFRESH_TOKEN_KEY = "trace.mobile.refresh_token";

export async function saveTokens(tokens: AuthTokens): Promise<void> {
  await SecureStore.setItemAsync(ACCESS_TOKEN_KEY, tokens.access_token);
  await SecureStore.setItemAsync(REFRESH_TOKEN_KEY, tokens.refresh_token);
}

export async function loadTokens(): Promise<AuthTokens | null> {
  const [access_token, refresh_token] = await Promise.all([
    SecureStore.getItemAsync(ACCESS_TOKEN_KEY),
    SecureStore.getItemAsync(REFRESH_TOKEN_KEY),
  ]);

  if (!access_token || !refresh_token) {
    return null;
  }

  return { access_token, refresh_token, token_type: "bearer" };
}

export async function clearTokens(): Promise<void> {
  await Promise.all([
    SecureStore.deleteItemAsync(ACCESS_TOKEN_KEY),
    SecureStore.deleteItemAsync(REFRESH_TOKEN_KEY),
  ]);
}