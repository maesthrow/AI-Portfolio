// ---- RAG types ----
export type AskRequest = {
  question: string;
  k?: number;
  collection?: string;
  system_prompt?: string | null;
};

export type AskSource = {
  id?: string;
  type?: string | null;
  title?: string | null;
  url?: string | null;
  score?: number;
  chunk?: string | null;
};

export type AskResponse = {
  answer: string;
  sources: AskSource[];
  found: number;
  collection: string;
  model: string;
};

// ---- Content API types ----
export type Technology = { id: number; name: string };

// Список проектов (лайт-DTO)
export type Project = {
  id: number;
  name: string;
  description?: string | null;
  period?: string | null;
  technologies?: string[];
  company_name?: string | null;
  company_website?: string | null;
};

// Детальная модель проекта (расширение Project)
export type Achievement = {
  title: string;
  description?: string | null;
  links: string[];
};

export type Doc = {
  title: string;
  url: string;
  doc_type?: string | null;
};

export type ProjectDetail = Project & {
  achievements: Achievement[];
  documents: Doc[];
};

// ---- env ----
const RAG = process.env.NEXT_PUBLIC_RAG_API_URL ?? "http://localhost:8004";
const CONTENT = process.env.NEXT_PUBLIC_CONTENT_API_URL ?? "http://localhost:8003";
const DEFAULT_COLLECTION = process.env.NEXT_PUBLIC_RAG_COLLECTION ?? "portfolio";

// ---- helpers ----
async function getJSON<T>(url: string): Promise<T> {
  const r = await fetch(url, { cache: "no-store" });
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return (await r.json()) as T;
}

async function postJSON<T>(url: string, body: unknown): Promise<T> {
  const r = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json; charset=utf-8" },
    body: JSON.stringify(body),
    cache: "no-store",
  });
  if (!r.ok) {
    const t = await r.text().catch(() => "");
    throw new Error(`POST ${url} -> ${r.status} ${r.statusText}: ${t}`);
  }
  return (await r.json()) as T;
}

// ---- RAG ----
export async function askRag(req: AskRequest): Promise<AskResponse> {
  return postJSON<AskResponse>(`${RAG}/ask`, {
    k: 10,
    collection: DEFAULT_COLLECTION,
    ...req,
  });
}

// ---- Content API ----
export async function getTechnologies(q?: string): Promise<Technology[]> {
  const qs = q ? `?q=${encodeURIComponent(q)}` : "";
  return getJSON<Technology[]>(`${CONTENT}/technologies${qs}`);
}

export async function getProjects(params?: { technology_id?: number[] }): Promise<Project[]> {
  const qp = new URLSearchParams();
  params?.technology_id?.forEach((id) => qp.append("technology_id", String(id)));
  const tail = qp.toString() ? `?${qp.toString()}` : "";
  return getJSON<Project[]>(`${CONTENT}/projects${tail}`);
}

// детальная страница теперь возвращает ProjectDetail (с achievements/documents)
export async function getProject(id: number | string): Promise<ProjectDetail> {
  return getJSON<ProjectDetail>(`${CONTENT}/projects/${id}`);
}
