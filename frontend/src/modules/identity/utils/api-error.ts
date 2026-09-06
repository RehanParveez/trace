import axios from "axios";

export function getApiErrorMessage(
  error: unknown,
  fallback = "Something went wrong. Please try again.",
): string {
  if (axios.isAxiosError(error)) {
    const data = error.response?.data as
      | {
          error?: {
            code?: string;
            message?: string;
          };
          detail?: string | Array<{ msg?: string }>;
          message?: string;
        }
      | undefined;

    if (typeof data?.error?.message === "string") {
      return data.error.message;
    }

    if (typeof data?.detail === "string") {
      return data.detail;
    }

    if (Array.isArray(data?.detail) && data.detail.length > 0) {
      const first = data.detail[0];
      if (typeof first?.msg === "string") {
        return first.msg;
      }
    }

    if (typeof data?.message === "string") {
      return data.message;
    }

    if (error.response?.status === 429) {
      return "Too many requests. Please try again later.";
    }
  }

  if (error instanceof Error && error.message) {
    return error.message;
  }

  return fallback;
}

export function getApiErrorCode(error: unknown): string | undefined {
  if (!axios.isAxiosError(error)) return undefined;

  const data = error.response?.data as
    | { error?: { code?: string } }
    | undefined;

  return data?.error?.code;
}