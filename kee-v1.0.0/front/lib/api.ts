/** Same-origin by default (Next rewrite → backend). Avoids CORS / Failed to fetch. */
export const API = process.env.NEXT_PUBLIC_KEE_API_URL || "/api/v1";

export async function post(path: string, body: unknown) {
  const r = await fetch(`${API}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function get(path: string) {
  const r = await fetch(`${API}${path}`, { cache: "no-store" });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function put(path: string, body: unknown) {
  const r = await fetch(`${API}${path}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function upload(path: string, form: FormData) {
  const r = await fetch(`${API}${path}`, { method: "POST", body: form });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export type JobLog = {
  ts?: string;
  level?: string;
  phase?: string;
  message: string;
};

export type JobStatus = {
  id?: string;
  kind?: string;
  status: string;
  progress: number;
  total: number;
  phase?: string | null;
  logs?: JobLog[];
  detail?: Record<string, unknown>;
  error?: string;
};

export async function pollJob(
  jobId: string,
  onTick?: (job: JobStatus) => void,
  opts?: { intervalMs?: number; timeoutMs?: number },
) {
  const interval = opts?.intervalMs ?? 600;
  const timeout = opts?.timeoutMs ?? 10 * 60 * 1000;
  const start = Date.now();
  while (Date.now() - start < timeout) {
    const job = (await get(`/jobs/${jobId}`)) as JobStatus;
    onTick?.(job);
    if (job.status === "done" || job.status === "failed") return job;
    await new Promise((r) => setTimeout(r, interval));
  }
  throw new Error("Job poll timeout");
}
