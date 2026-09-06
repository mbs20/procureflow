export interface LineItem {
  id?: string;
  position?: number;
  description: string;
  quantity: number;
  unit: string;
}

export interface Criterion {
  id?: string;
  name: string;
  description?: string;
  weight: number;
  direction?: "lower_is_better" | "higher_is_better";
  is_knockout?: boolean;
  data_type?: "price" | "days" | "percentage" | "enum" | "boolean" | "text";
}

export interface RFQ {
  id: string;
  title: string;
  description?: string;
  category: string;
  status: "draft" | "active" | "evaluating" | "decided" | "archived";
  reference_currency: string;
  created_by: string;
  is_archived: boolean;
  created_at: string;
  updated_at: string;
  line_items: LineItem[];
  criteria: Criterion[];
}

export interface PaginatedRFQs {
  items: RFQ[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

const API_BASE = import.meta.env.VITE_API_BASE_URL || "";
const DEV_API_KEY = "procureflow_dev_api_key_12345";

export async function fetchRFQs(params?: {
  include_archived?: boolean;
  status?: string;
  category?: string;
  page?: number;
  page_size?: number;
}): Promise<PaginatedRFQs> {
  const query = new URLSearchParams();
  if (params?.include_archived) query.set("include_archived", "true");
  if (params?.status) query.set("status", params.status);
  if (params?.category) query.set("category", params.category);
  if (params?.page) query.set("page", params.page.toString());
  if (params?.page_size) query.set("page_size", params.page_size.toString());

  const res = await fetch(`${API_BASE}/api/v1/rfqs?${query.toString()}`);
  if (!res.ok) throw new Error(`Failed to fetch RFQs: ${res.statusText}`);
  return res.json();
}

export async function fetchRFQById(id: string): Promise<RFQ> {
  const res = await fetch(`${API_BASE}/api/v1/rfqs/${id}`);
  if (!res.ok) throw new Error(`Failed to fetch RFQ ${id}: ${res.statusText}`);
  return res.json();
}

export async function createRFQ(payload: {
  title: string;
  description?: string;
  category: string;
  reference_currency: string;
  line_items: LineItem[];
  criteria: Criterion[];
}): Promise<RFQ> {
  const res = await fetch(`${API_BASE}/api/v1/rfqs`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": DEV_API_KEY,
    },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to create RFQ: ${res.statusText}`);
  }
  return res.json();
}

export async function archiveRFQ(id: string): Promise<RFQ> {
  const res = await fetch(`${API_BASE}/api/v1/rfqs/${id}/archive`, {
    method: "POST",
    headers: { "X-API-Key": DEV_API_KEY },
  });
  if (!res.ok) throw new Error(`Failed to archive RFQ: ${res.statusText}`);
  return res.json();
}

export async function unarchiveRFQ(id: string): Promise<RFQ> {
  const res = await fetch(`${API_BASE}/api/v1/rfqs/${id}/unarchive`, {
    method: "POST",
    headers: { "X-API-Key": DEV_API_KEY },
  });
  if (!res.ok) throw new Error(`Failed to restore RFQ: ${res.statusText}`);
  return res.json();
}

export async function cloneRFQ(id: string, newTitle?: string): Promise<RFQ> {
  const query = newTitle ? `?new_title=${encodeURIComponent(newTitle)}` : "";
  const res = await fetch(`${API_BASE}/api/v1/rfqs/${id}/clone${query}`, {
    method: "POST",
    headers: { "X-API-Key": DEV_API_KEY },
  });
  if (!res.ok) throw new Error(`Failed to clone RFQ: ${res.statusText}`);
  return res.json();
}

export async function updateCriteria(id: string, criteria: Criterion[]): Promise<RFQ> {
  const res = await fetch(`${API_BASE}/api/v1/rfqs/${id}/criteria`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": DEV_API_KEY,
    },
    body: JSON.stringify(criteria),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to update criteria: ${res.statusText}`);
  }
  return res.json();
}
