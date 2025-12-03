import { Project } from "@/lib/types";

const domainLabels: Record<string, { label: string; tone: string }> = {
  cv: { label: "CV", tone: "border-accent/40 bg-accent/10 text-accent" },
  rag: { label: "RAG", tone: "border-accent-alt/50 bg-accent-alt/15 text-accent-soft" },
  backend: { label: "Backend", tone: "border-slate-700 bg-slate-900/70 text-slate-100" },
  mlops: { label: "MLOps", tone: "border-amber-200/50 bg-amber-200/10 text-amber-200" },
  other: { label: "Other", tone: "border-slate-700/80 bg-slate-800/70 text-slate-100" }
};

type ProjectCardProps = {
  project: Project;
};

function normalizeTech(value: string | { id?: string | number; name?: string }) {
  if (typeof value === "string") return value;
  if (value?.name) return value.name;
  if (value?.id !== undefined) return String(value.id);
  return null;
}

function shortDescription(md?: string | null) {
  if (!md) return null;
  const lines = md
    .split("\n")
    .map((line) => line.replace(/^[*-]\s*/, "").trim())
    .filter(Boolean);
  if (!lines.length) return null;
  return lines.slice(0, 2).join(" ");
}

export default function ProjectCard({ project }: ProjectCardProps) {
  const domainKey = project.domain?.toString().toLowerCase();
  const domain = domainKey ? domainLabels[domainKey] : null;
  const techTags = (project.technologies || [])
    .map((tech) => normalizeTech(tech as any))
    .filter(Boolean)
    .slice(0, 4) as string[];
  const description = shortDescription(project.description_md || (project as any).description);

  return (
    <div className="group relative flex flex-col gap-5 rounded-3xl border border-[#00ffc3]/25 bg-gradient-to-br from-black/60 via-bg-panel/80 to-black/50 p-8 shadow-[0_0_15px_rgba(0,255,200,0.14)] transition-transform duration-300 hover:-translate-y-1.5 hover:scale-[1.02] hover:border-[#00ffc3]/60 hover:shadow-[0_0_45px_rgba(0,255,200,0.35)]">
      <div className="absolute inset-px rounded-[22px] bg-gradient-to-r from-accent/10 via-transparent to-accent-alt/10 opacity-0 transition-opacity duration-500 group-hover:opacity-70" />
      <div className="relative flex flex-wrap items-center gap-2">
        {domain ? (
          <span
            className={`rounded-full border px-3 py-1 text-[11px] font-semibold uppercase tracking-wide shadow-[0_0_12px_rgba(0,255,200,0.25)] ${domain.tone}`}
          >
            {domain.label}
          </span>
        ) : null}
        {techTags.map((tech) => (
          <span
            key={tech}
            className="rounded-full border border-[#00ffc3]/30 bg-black/60 px-3 py-1 text-[11px] text-slate-200 shadow-[0_0_8px_rgba(0,255,200,0.2)]"
          >
            {tech}
          </span>
        ))}
      </div>

      <div className="relative space-y-2">
        <p className="text-2xl font-semibold leading-tight text-slate-50">{project.name}</p>
        {description ? (
          <p className="text-sm leading-relaxed text-slate-300">{description}</p>
        ) : null}
      </div>

      <div className="relative mt-auto flex flex-wrap items-center justify-between gap-3 text-sm text-slate-300">
        {project.period ? (
          <span className="text-slate-400">{project.period}</span>
        ) : (
          <span className="text-transparent">—</span>
        )}
        <div className="flex flex-wrap gap-3">
          {project.repo_url ? (
            <a
              href={project.repo_url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-2 rounded-full border border-[#00ffc3]/50 bg-black/50 px-4 py-1.5 font-semibold text-accent shadow-[0_0_18px_rgba(0,255,200,0.25)] transition-transform duration-200 hover:-translate-y-0.5 hover:text-accent-soft"
            >
              GitHub
            </a>
          ) : null}
          {project.demo_url ? (
            <a
              href={project.demo_url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-2 rounded-full border border-accent-alt/60 bg-accent-alt/10 px-4 py-1.5 font-semibold text-accent-soft shadow-[0_0_18px_rgba(139,92,246,0.3)] transition-transform duration-200 hover:-translate-y-0.5"
            >
              Demo
            </a>
          ) : null}
        </div>
      </div>
    </div>
  );
}
