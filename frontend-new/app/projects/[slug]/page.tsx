import Link from "next/link";
import { notFound } from "next/navigation";
import ReactMarkdown from "react-markdown";

import Shell from "@/components/layout/Shell";
import { getProjectBySlug } from "@/lib/api";
import { ProjectDetail } from "@/lib/types";

const domainLabels: Record<string, { label: string; tone: string }> = {
  cv: { label: "CV", tone: "border-accent/40 bg-accent/10 text-accent" },
  rag: { label: "RAG", tone: "border-accent-alt/50 bg-accent-alt/15 text-accent-soft" },
  llm: { label: "LLM", tone: "border-purple-400/50 bg-purple-400/10 text-purple-300" },
  backend: { label: "Backend", tone: "border-slate-700 bg-slate-900/70 text-slate-100" },
  mlops: { label: "MLOps", tone: "border-amber-200/50 bg-amber-200/10 text-amber-200" },
  other: { label: "Other", tone: "border-slate-700/80 bg-slate-800/70 text-slate-100" }
};

function normalizeTech(value: string | { id?: string | number; name?: string }) {
  if (typeof value === "string") return value;
  if (value?.name) return value.name;
  if (value?.id !== undefined) return String(value.id);
  return null;
}

type PageProps = {
  params: { slug: string };
};

export default async function ProjectDetailPage({ params }: PageProps) {
  let project: ProjectDetail | null = null;
  try {
    project = await getProjectBySlug(params.slug);
  } catch {
    notFound();
  }

  if (!project) {
    notFound();
  }

  const domainKey = project.domain?.toString().toLowerCase();
  const domain = domainKey ? domainLabels[domainKey] : null;
  const techTags = (project.technologies || [])
    .map((tech) => normalizeTech(tech as any))
    .filter(Boolean) as string[];

  const descriptionContent = project.long_description_md || project.description_md;

  return (
    <Shell>
      <div className="mx-auto flex max-w-5xl flex-col gap-10 px-4 pb-16 pt-10 sm:px-6 lg:px-0">
        <div className="flex flex-col gap-6 rounded-3xl border border-[#00ffc3]/25 bg-gradient-to-br from-black/60 via-bg-panel/80 to-black/50 p-7 shadow-[0_0_30px_rgba(0,255,200,0.18)]">
          <div className="flex flex-wrap items-center gap-3">
            {domain ? (
              <span
                className={`rounded-full border px-3 py-1 text-[11px] font-semibold uppercase tracking-wide shadow-[0_0_12px_rgba(0,255,200,0.25)] ${domain.tone}`}
              >
                {domain.label}
              </span>
            ) : null}
            {project.featured ? (
              <span className="rounded-full border border-accent/60 bg-accent/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-wide text-accent shadow-[0_0_12px_rgba(0,255,200,0.25)]">
                Featured
              </span>
            ) : null}
          </div>

          <h1 className="text-2xl font-semibold text-slate-50 sm:text-3xl">{project.name}</h1>

          <div className="flex flex-wrap items-center gap-4 text-base text-slate-300">
            {project.period ? <span className="text-slate-400">{project.period}</span> : null}
            {project.company_name ? (
              <>
                {project.period ? <span className="text-slate-600">|</span> : null}
                {project.company_website ? (
                  <a
                    href={project.company_website}
                    target="_blank"
                    rel="noreferrer"
                    className="text-accent hover:text-accent-soft"
                  >
                    {project.company_name}
                  </a>
                ) : (
                  <span className="text-accent">{project.company_name}</span>
                )}
              </>
            ) : null}
          </div>

          <div className="flex flex-wrap gap-3">
            {project.repo_url ? (
              <a
                href={project.repo_url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-2 rounded-full border border-[#00ffc3]/50 bg-black/50 px-5 py-2 font-semibold text-accent shadow-[0_0_18px_rgba(0,255,200,0.25)] transition-transform duration-200 hover:-translate-y-0.5 hover:text-accent-soft"
              >
                GitHub
              </a>
            ) : null}
            {project.demo_url ? (
              <a
                href={project.demo_url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-2 rounded-full border border-accent-alt/60 bg-accent-alt/10 px-5 py-2 font-semibold text-accent-soft shadow-[0_0_18px_rgba(139,92,246,0.3)] transition-transform duration-200 hover:-translate-y-0.5"
              >
                Demo
              </a>
            ) : null}
          </div>
        </div>

        {descriptionContent ? (
          <div className="rounded-2xl border border-slate-700/60 bg-slate-900/40 p-6 shadow-[0_0_18px_rgba(0,0,0,0.4)]">
            <h2 className="mb-4 text-xl font-semibold text-slate-50">Описание проекта</h2>
            <ReactMarkdown
              className="prose prose-invert max-w-none text-slate-100/90"
              components={{
                ul: ({ ...props }) => (
                  <ul className="ml-5 list-disc space-y-3 marker:text-accent" {...props} />
                ),
                li: ({ ...props }) => <li className="text-slate-100/90" {...props} />,
                h1: ({ ...props }) => (
                  <h1 className="mb-4 text-2xl font-bold text-slate-50" {...props} />
                ),
                h2: ({ ...props }) => (
                  <h2 className="mb-3 mt-6 text-xl font-semibold text-slate-100" {...props} />
                ),
                h3: ({ ...props }) => (
                  <h3 className="mb-2 mt-4 text-lg font-medium text-slate-200" {...props} />
                ),
                p: ({ ...props }) => <p className="mb-4 leading-relaxed" {...props} />,
                a: ({ href, ...props }) => (
                  <a
                    href={href}
                    target="_blank"
                    rel="noreferrer"
                    className="text-accent hover:text-accent-soft"
                    {...props}
                  />
                ),
                code: ({ ...props }) => (
                  <code
                    className="rounded bg-slate-800 px-1.5 py-0.5 font-mono text-sm text-accent-soft"
                    {...props}
                  />
                ),
                pre: ({ ...props }) => (
                  <pre
                    className="overflow-x-auto rounded-lg bg-slate-800/80 p-4 font-mono text-sm"
                    {...props}
                  />
                )
              }}
            >
              {descriptionContent}
            </ReactMarkdown>
          </div>
        ) : null}

        {techTags.length > 0 ? (
          <div className="rounded-2xl border border-slate-700/60 bg-slate-900/40 p-6 shadow-[0_0_18px_rgba(0,0,0,0.4)]">
            <h2 className="mb-4 text-xl font-semibold text-slate-50">Технологии</h2>
            <div className="flex flex-wrap gap-3">
              {techTags.map((tech) => (
                <span
                  key={tech}
                  className="rounded-full border border-[#00ffc3]/40 bg-accent/10 px-4 py-1.5 text-sm font-medium text-slate-100 shadow-[0_0_10px_rgba(0,255,200,0.2)]"
                >
                  {tech}
                </span>
              ))}
            </div>
          </div>
        ) : null}

        <div className="flex justify-start">
          <Link
            href="/#projects"
            className="inline-flex items-center gap-2 rounded-full border border-[#00ffc3]/50 px-4 py-2 text-sm font-medium text-accent transition hover:-translate-y-0.5 hover:border-accent hover:text-accent-soft"
          >
            &#8592; Назад к проектам
          </Link>
        </div>
      </div>
    </Shell>
  );
}
