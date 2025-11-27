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
  role: string;
  company: string;
  companyUrl?: string | null;
  period: string;
  kind: "current" | "previous" | "founder";
  description: string;
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
  tags: string[];
};

export type Project = {
  id: number;
  name: string;
  description?: string | null;
  period?: string | null;
  company_name?: string | null;
  company_website?: string | null;
  technologies?: string[];
  domain?: "cv" | "rag" | "backend" | "mlops" | "other";
  featured?: boolean;
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
};
