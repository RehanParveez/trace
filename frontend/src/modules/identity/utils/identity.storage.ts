const ACCESS_TOKEN_KEY = "trace.access_token";
const REFRESH_TOKEN_KEY = "trace.refresh_token";

export const identityStorage = {
  getAccessToken(): string | null {
    return localStorage.getItem(ACCESS_TOKEN_KEY);
  },

  getRefreshToken(): string | null {
    return localStorage.getItem(REFRESH_TOKEN_KEY);
  },

  setTokens(
    accessToken: string,
    refreshToken: string,
  ): void {
    localStorage.setItem(
      ACCESS_TOKEN_KEY,
      accessToken,
    );

    localStorage.setItem(
      REFRESH_TOKEN_KEY,
      refreshToken,
    );
  },

  clear(): void {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
  },

  hasSession(): boolean {
    return Boolean(
      localStorage.getItem(ACCESS_TOKEN_KEY) &&
      localStorage.getItem(REFRESH_TOKEN_KEY),
    );
  },
};