export function getApiErrorCode(error: unknown): string | null {
  const data = (error as { response?: { data?: { error?: { code?: unknown } } } } | null)?.response?.data;
  const code = data?.error?.code;
  return typeof code === "string" ? code : null;
}