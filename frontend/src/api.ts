import type {
  Briefing,
  Cash,
  EventsResponse,
  Health,
  Queue,
  Run,
  TicketDetail,
  TicketList,
  TicketSummary,
} from "./types";

// The FastAPI backend from Problem 7.
export const API_BASE = "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

function messageFrom(body: unknown, fallback: string): string {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (detail && typeof detail === "object" && "error" in detail) {
      const d = detail as { error: string; short_by?: number };
      return d.short_by ? `${d.error} Short by $${d.short_by.toFixed(2)}.` : d.error;
    }
    if (Array.isArray(detail)) return detail.map((d) => d.msg ?? String(d)).join("; ");
  }
  return fallback;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    });
  } catch {
    throw new ApiError(0, "Can't reach the backend at localhost:8000. Is uvicorn running?");
  }
  const body = await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(res.status, messageFrom(body, `${res.status} ${res.statusText}`));
  return body as T;
}

const post = <T>(path: string, data?: unknown) =>
  request<T>(path, { method: "POST", body: data === undefined ? undefined : JSON.stringify(data) });

export const api = {
  health: () => request<Health>("/api/health"),
  tickets: () => request<TicketList>("/api/tickets"),
  ticket: (id: number) => request<TicketDetail>(`/api/tickets/${id}`),
  summary: (id: number) => request<TicketSummary>(`/api/tickets/${id}/summary`),
  runTicket: (id: number) => post<Run>(`/api/tickets/${id}/run`),
  run: (runId: string) => request<Run>(`/api/runs/${runId}`),
  events: (params: { runId?: string; ticketId?: number; after?: number; limit?: number }) => {
    const q = new URLSearchParams();
    if (params.runId) q.set("run_id", params.runId);
    if (params.ticketId !== undefined) q.set("ticket_id", String(params.ticketId));
    if (params.after !== undefined) q.set("after", String(params.after));
    q.set("limit", String(params.limit ?? 300));
    return request<EventsResponse>(`/api/events?${q}`);
  },
  queue: () => request<Queue>("/api/payment-requests?status=pending"),
  approve: (requestId: number, approvedBy: string) =>
    post<{ balance_after: number; amount: number; ticket_id: number | null; ticket_resolved: boolean }>(
      `/api/payment-requests/${requestId}/approve`,
      { approved_by: approvedBy },
    ),
  reject: (requestId: number, decidedBy: string, reason: string) =>
    post(`/api/payment-requests/${requestId}/reject`, { decided_by: decidedBy, reason }),
  resolve: (ticketId: number, resolvedBy: string) =>
    post(`/api/tickets/${ticketId}/resolve`, { resolved_by: resolvedBy, note: "Reviewed on the dashboard." }),
  cash: () => request<Cash>("/api/cash"),
  briefing: () => request<Briefing>("/api/briefing"),
  addNote: (ticketId: number, author: string, note: string) =>
    post(`/api/tickets/${ticketId}/notes`, { author, note }),
  reset: () => post("/api/reset"),
};
