import { Project } from "@/lib/types";

const domainLabels: Record<
  NonNullable<Project["domain"]>,
  { label: string; tone: string }
> = {
  cv: { label: "CV", tone: "bg-accent/10 text-accent" },
  rag: { label: "RAG", tone: "bg-accent-alt/20 text-accent-soft" },
  backend: { label: "Backend", tone: "bg-slate-800 text-slate-200" },
  mlops: { label: "MLOps", tone: "bg-amber-200/10 text-amber-200" },
  other: { label: "Other", tone: "bg-slate-700/60 text-slate-100" }
};

type ProjectCardProps = {
  project: Project;
};

export default function ProjectCard({ project }: ProjectCardProps) {
  const domain = project.domain ? domainLabels[project.domain] : null;

  return (
    <div className="flex flex-col gap-3 rounded-2xl border border-accent/30 bg-gradient-to-br from-black/60 via-bg-panel/80 to-black/40 p-5 shadow-neon transition-transform duration-200 hover:-translate-y-1 hover:shadow-neon-strong">
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-lg font-semibold text-slate-50">{project.name}</p>
          {project.period ? (
            <p className="text-xs uppercase tracking-wide text-slate-400">{project.period}</p>
          ) : null}
        </div>
        {domain ? (
          <span className={`rounded-full px-3 py-1 text-xs font-semibold ${domain.tone}`}>
            {domain.label}
          </span>
        ) : null}
      </div>
      {project.description ? (
        <p className="text-sm leading-relaxed text-slate-200">{project.description}</p>
      ) : null}
      {project.technologies?.length ? (
        <div className="flex flex-wrap gap-2">
          {project.technologies.map((tech) => (
            <span
              key={tech}
              className="rounded-full border border-accent/30 bg-black/50 px-3 py-1 text-xs text-slate-200"
            >
              {tech}
            </span>
          ))}
        </div>
      ) : null}
      {(project.repo_url || project.demo_url) && (
        <div className="flex flex-wrap gap-3 pt-1 text-sm">
          {project.repo_url ? (
            <a
              href={project.repo_url}
              className="text-accent hover:text-accent-soft"
              target="_blank"
              rel="noreferrer"
            >
              GitHub →
            </a>
          ) : null}
          {project.demo_url ? (
            <a
              href={project.demo_url}
              className="text-accent hover:text-accent-soft"
              target="_blank"
              rel="noreferrer"
            >
              Demo →
            </a>
          ) : null}
        </div>
      )}
    </div>
  );
}
