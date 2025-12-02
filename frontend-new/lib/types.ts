export type Profile = {
  name: string;
  title: string;
  subtitle?: string;
  location?: string;
  status?: string;
  avatarUrl?: string | null;
};

export type ExperienceItem = {
  id: number;
  company_slug: string;
  company_name: string | null;
  company_url?: string | null;
  role: string;
  start_date: string;
  end_date: string | null;
  is_current: boolean;
  kind: "commercial" | "personal" | string;
  company_summary_md?: string | null;
  company_role_md?: string | null;
  order_index?: number;
};

export type ExperienceProject = {
  id: number;
  name: string;
  slug: string;
  period?: string | null;
  description_md: string;
  achievements_md: string;
  order_index: number;
  technologies?: string[];
};

export type ExperienceDetail = {
  company: ExperienceItem;
  projects: ExperienceProject[];
};

export type StatItem = {
  id: string;
  label: string;
  value: string;
  hint?: string;
};

export type TechFocusItem = {
  id: string;
  label: string;
  tags: (string | { id?: string | number; name?: string; order_index?: number })[];
};

export type Project = {
  id: number;
  slug: string;
  name: string;
  description_md?: string | null;
  period?: string | null;
  company_name?: string | null;
  company_website?: string | null;
  technologies: (string | { id?: string | number; name?: string })[];
  domain?: "cv" | "rag" | "backend" | "mlops" | "other" | string | null;
  featured: boolean;
  repo_url?: string | null;
  demo_url?: string | null;
};

export type Publication = {
  id: number;
  title: string;
  year: number;
  source: "Habr" | "GitHub" | "Blog" | "Other";
  url: string;
  badge?: string | null;
};

export type Contact = {
  kind: "email" | "telegram" | "github" | "linkedin" | "other";
  label: string;
  value: string;
  url: string;
};

export type AgentMessage = {
  id: string;
  role: "user" | "agent";
  content: string;
  createdAt: number;
  tempId?: string;
  status?: "streaming" | "done" | "error" | "stopped";
};
