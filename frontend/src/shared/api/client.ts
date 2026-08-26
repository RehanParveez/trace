import axios, {type AxiosError, type InternalAxiosRequestConfig,
} from "axios";
import { identityStorage } from "../../modules/identity/utils/identity.storage";

export const apiClient = axios.create({
  baseURL:
    import.meta.env.VITE_API_BASE_URL ??
    "/api/v1",

  headers: {
    "Content-Type":
      "application/json",
  },
});

let refreshPromise:
  Promise<string | null> | null = null;

type RetryConfig =
  InternalAxiosRequestConfig & {
    _retry?: boolean;
  };

apiClient.interceptors.request.use(
  (config) => {
    const token =
      identityStorage.getAccessToken();

    if (token) {
      config.headers.Authorization =
        `Bearer ${token}`;
    }

    return config;
  },
);

apiClient.interceptors.response.use(
  (response) => response,

  async (error: AxiosError) => {
    const original =
      error.config as
        | RetryConfig
        | undefined;

    const status =
      error.response?.status;

    if (
      !original ||
      status !== 401 ||
      original._retry
    ) {
      return Promise.reject(error);
    }

    const url =
      original.url ?? "";

    if (
      url.includes("/auth/login") ||
      url.includes("/auth/refresh")
    ) {
      return Promise.reject(error);
    }

    const refreshToken =
      identityStorage.getRefreshToken();

    if (!refreshToken) {
      identityStorage.clear();

      return Promise.reject(error);
    }

    original._retry = true;

    if (!refreshPromise) {
      refreshPromise =
        apiClient
          .post("/auth/refresh", {
            refresh_token:
              refreshToken,
          })
          .then(({ data }) => {
            identityStorage.setTokens(
              data.access_token,
              data.refresh_token,
            );

            return data.access_token as string;
          })
          .catch(() => {
            identityStorage.clear();

            return null;
          })
          .finally(() => {
            refreshPromise = null;
          });
    }

    const nextToken =
      await refreshPromise;

    if (!nextToken) {
      return Promise.reject(error);
    }

    original.headers.Authorization =
      `Bearer ${nextToken}`;

    return apiClient(original);
  },
);