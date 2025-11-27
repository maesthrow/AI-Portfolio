import {
  Contact,
  ExperienceItem,
  Profile,
  Project,
  Publication,
  StatItem,
  TechFocusItem
} from "./types";

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
