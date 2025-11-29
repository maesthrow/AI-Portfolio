import { Project } from "@/lib/types";

const domainLabels: Record<
  NonNullable<Project["domain"]>,
  { label: string; tone: string }
> = {
  cv: { label: "CV", tone: "bg-accent/15 text-accent" },
  rag: { label: "RAG", tone: "bg-accent-alt/20 text-accent-soft" },
  backend: { label: "Backend", tone: "bg-slate-800 text-slate-200" },
  mlops: { label: "MLOps", tone: "bg-amber-200/10 text-amber-200" },
  other: { label: "Other", tone: "bg-slate-700/60 text-slate-100" }
};

type ProjectCardProps = {
  project: Project;
};

function normalizeTech(value: string | { id?: string | number; name?: string }): string {
  if (typeof value === "string") return value;
  if (value?.name) return value.name;
  if (value?.id !== undefined) return String(value.id);
  return "tech";
}

export default function ProjectCard({ project }: ProjectCardProps) {
  const domain = project.domain ? domainLabels[project.domain] : null;

  return (
    <div className="group flex flex-col gap-4 rounded-3xl border border-[#00ffc3]/25 bg-gradient-to-br from-black/60 via-bg-panel/80 to-black/50 p-8 shadow-[0_0_25px_rgba(0,255,200,0.2)] transition-transform duration-300 hover:-translate-y-1 hover:scale-105 hover:border-[#00ffc3]/60 hover:shadow-[0_0_45px_rgba(0,255,200,0.35)]">
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-xl font-semibold text-slate-50">{project.name}</p>
          {project.period ? (
            <p className="text-xs uppercase tracking-wide text-slate-400">{project.period}</p>
          ) : null}
        </div>
        {domain ? (
          <span className={`rounded-full border border-[#00ffc3]/40 px-3 py-1 text-xs font-semibold shadow-[0_0_10px_rgba(0,255,200,0.25)] ${domain.tone}`}>
            {domain.label}
          </span>
        ) : null}
      </div>
      {project.description ? (
        <p className="text-[1.05rem] leading-relaxed text-gray-300">{project.description}</p>
      ) : null}
      {project.technologies?.length ? (
        <div className="flex flex-wrap gap-3 pt-1">
          {project.technologies.map((tech) => (
            <span
              key={normalizeTech(tech as any)}
              className="rounded-full border border-[#00ffc3]/30 bg-black/50 px-3 py-1 text-xs text-slate-200 shadow-[0_0_8px_rgba(0,255,200,0.2)]"
            >
              {normalizeTech(tech as any)}
            </span>
          ))}
        </div>
      ) : null}
      {(project.repo_url || project.demo_url) && (
        <div className="flex flex-wrap gap-4 pt-2 text-sm">
          {project.repo_url ? (
            <a
              href={project.repo_url}
              className="font-semibold text-accent hover:text-accent-soft"
              target="_blank"
              rel="noreferrer"
            >
              GitHub ��'
            </a>
          ) : null}
          {project.demo_url ? (
            <a
              href={project.demo_url}
              className="font-semibold text-accent hover:text-accent-soft"
              target="_blank"
              rel="noreferrer"
            >
              Demo ��'
            </a>
          ) : null}
        </div>
      )}
    </div>
  );
}
