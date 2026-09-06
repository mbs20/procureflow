export interface ServiceStatus {
  status: string;
  latency_ms?: number;
  details?: string;
}

export interface HealthResponse {
  status: string;
  version: string;
  environment: string;
  database: ServiceStatus;
  redis: ServiceStatus;
  celery: ServiceStatus;
}

export interface RootResponse {
  name: string;
  version: string;
  status: string;
  docs_url: string;
  health_url: string;
}

const API_BASE = import.meta.env.VITE_API_BASE_URL || "";

export async function fetchHealth(): Promise<HealthResponse> {
  const res = await fetch(`${API_BASE}/api/v1/health`);
  if (!res.ok) {
    throw new Error(`Health check failed: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchRoot(): Promise<RootResponse> {
  const res = await fetch(`${API_BASE}/`);
  if (!res.ok) {
    throw new Error(`Root fetch failed: ${res.statusText}`);
  }
  return res.json();
}
