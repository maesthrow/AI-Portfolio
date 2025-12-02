import {
  Contact,
  ExperienceDetail,
  ExperienceItem,
  Profile,
  Project,
  Publication,
  StatItem,
  TechFocusItem
} from "./types";

export type ChatStreamEvent =
  | { type: "start"; message_id: string; created_at: string }
  | { type: "delta"; content: string }
  | { type: "end"; message_id: string; usage?: any }
  | { type: "error"; message: string };

const CONTENT_API_BASE = process.env.CONTENT_API_BASE || process.env.NEXT_PUBLIC_CONTENT_API_BASE;
const AGENT_API_BASE = process.env.AGENT_API_BASE || process.env.NEXT_PUBLIC_AGENT_API_BASE;

if (!CONTENT_API_BASE) {
  console.warn("CONTENT_API_BASE is not set; API requests will fail at runtime.");
}

if (!AGENT_API_BASE) {
  console.warn("AGENT_API_BASE is not set; agent requests will fail at runtime.");
}

async function getJson<T>(path: string): Promise<T> {
  const base = CONTENT_API_BASE;
  if (!base) {
    throw new Error("CONTENT_API_BASE is missing");
  }
  const res = await fetch(`${base}${path}`, {
    next: { revalidate: 60 }
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch ${path}`);
  }
  return res.json();
}

export async function getProfile(): Promise<Profile> {
  return getJson("/profile");
}

export async function getExperience(): Promise<ExperienceItem[]> {
  return getJson("/experience");
}

export async function getExperienceDetail(slug: string): Promise<ExperienceDetail> {
  return getJson(`/experience/${slug}`);
}

export async function getStats(): Promise<StatItem[]> {
  return getJson("/stats");
}

export async function getTechFocus(): Promise<TechFocusItem[]> {
  return getJson("/tech-focus");
}

export async function getProjects(): Promise<Project[]> {
  return getJson("/projects");
}

export async function getPublications(): Promise<Publication[]> {
  return getJson("/publications");
}

export async function getContacts(): Promise<Contact[]> {
  return getJson("/contacts");
}

export async function askAgent(question: string, sessionId: string) {
  const base = AGENT_API_BASE;
  if (!base) {
    throw new Error("AGENT_API_BASE is missing");
  }
  const res = await fetch(`${base}/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, session_id: sessionId })
  });
  if (!res.ok) {
    throw new Error("Agent request failed");
  }
  return res.json() as Promise<{ answer: string; sources?: string[] }>;
}

export async function callAgentStream(
  body: Record<string, unknown>,
  opts?: { signal?: AbortSignal }
) {
  const base = AGENT_API_BASE;
  if (!base) {
    throw new Error("AGENT_API_BASE is missing");
  }

  const res = await fetch(`${base}/api/v1/agent/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal: opts?.signal
  });

  if (!res.ok || !res.body) {
    throw new Error(`Stream request failed with status ${res.status}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  return {
    async *[Symbol.asyncIterator](): AsyncIterator<ChatStreamEvent> {
      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });

          let newlineIndex: number;
          while ((newlineIndex = buffer.indexOf("\n")) >= 0) {
            const line = buffer.slice(0, newlineIndex).trim();
            buffer = buffer.slice(newlineIndex + 1);

            if (!line) continue;
            try {
              const parsed = JSON.parse(line) as ChatStreamEvent;
              yield parsed;
            } catch (err) {
              console.error("Failed to parse stream line", line, err);
            }
          }
        }
      } finally {
        reader.releaseLock();
      }
    }
  };
}
