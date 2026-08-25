export type HealthResponse = {
  status: "healthy" | "unhealthy";
  version: string;
};

export async function getHealth(): Promise<HealthResponse> {
  const response = await fetch("http://localhost:8015/health");

  if (!response.ok) {
    throw new Error("Health check failed");
  }

  return response.json() as Promise<HealthResponse>;
}