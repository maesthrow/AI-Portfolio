import Link from "next/link";
import { notFound } from "next/navigation";
import ReactMarkdown from "react-markdown";

import Shell from "@/components/layout/Shell";
import { getExperienceDetail } from "@/lib/api";
import { ExperienceDetail } from "@/lib/types";

function formatPeriod(start?: string | null, end?: string | null, isCurrent?: boolean) {
  if (!start) return null;
  const startYear = new Date(start).getFullYear();
  const endYear = end ? new Date(end).getFullYear() : null;
  if (isCurrent || (!end && !endYear)) return `${startYear} — н.в.`;
  if (endYear) return `${startYear} — ${endYear}`;
  return `${startYear}`;
}

type PageProps = {
  params: { company_slug: string };
};

export default async function ExperienceCompanyPage({ params }: PageProps) {
  let detail: ExperienceDetail | null = null;
  try {
    detail = await getExperienceDetail(params.company_slug);
  } catch {
    notFound();
  }

  if (!detail) {
    notFound();
  }

  const { company, projects } = detail;
  const period = formatPeriod(company.start_date, company.end_date, company.is_current);

  return (
    <Shell>
      <div className="mx-auto flex max-w-5xl flex-col gap-10 px-4 pb-16 pt-10 sm:px-6 lg:px-0">
        <div className="flex flex-col gap-4 rounded-3xl border border-emerald-400/20 bg-black/60 p-7 shadow-[0_0_30px_rgba(0,255,200,0.18)]">
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-2xl font-semibold text-slate-50 sm:text-3xl">
              {company.role}
            </h1>
            <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-wide text-slate-200">
              <span
                className={`rounded-full px-2 py-0.5 ${
                  company.is_current
                    ? "border border-emerald-400/60 bg-emerald-400/10 text-emerald-200"
                    : "border border-slate-600/70 bg-slate-800/70 text-slate-200"
                }`}
              >
                {company.is_current ? "Текущее" : "Прошлое"}
              </span>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3 text-base text-slate-200">
            {company.company_url ? (
              <a
                href={company.company_url}
                target="_blank"
                rel="noreferrer"
                className="text-emerald-300 hover:text-emerald-200"
              >
                {company.company_name}
              </a>
            ) : (
              <span className="text-emerald-300">{company.company_name}</span>
            )}
            {company.company_name && period ? <span className="text-slate-500">·</span> : null}
            {period ? <span className="text-slate-400">{period}</span> : null}
          </div>

          {company.company_role_md ? (
            <div className="prose prose-invert max-w-none text-lg text-slate-100/90">
              <ReactMarkdown>{company.company_role_md}</ReactMarkdown>
            </div>
          ) : company.company_summary_md ? (
            <div className="prose prose-invert max-w-none text-lg text-slate-100/90">
              <ReactMarkdown>{company.company_summary_md}</ReactMarkdown>
            </div>
          ) : null}
        </div>

        <div className="flex flex-col gap-6">
          <h2 className="text-xl font-semibold text-slate-50 sm:text-2xl">Проекты и достижения в компании</h2>
          <div className="flex flex-col gap-6">
            {projects.map((proj) => (
              <div
                key={proj.id}
                className="rounded-2xl border border-slate-700/60 bg-slate-900/40 p-6 shadow-[0_0_18px_rgba(0,0,0,0.4)]"
              >
                <div className="flex flex-col gap-1">
                  <h3 className="text-lg font-semibold text-emerald-300">{proj.name}</h3>
                </div>
                <div className="mt-4 prose prose-invert max-w-none text-lg text-slate-100/90">
                  <ReactMarkdown>{proj.description_md}</ReactMarkdown>
                </div>
                <div className="mt-5 h-px bg-emerald-400/15" />
                <div className="mt-4">
                  <ReactMarkdown
                    className="prose prose-invert max-w-none text-slate-100/90"
                    components={{
                      ul: ({ ...props }) => (
                        <ul className="ml-5 list-disc space-y-3.5 marker:text-emerald-300" {...props} />
                      ),
                      li: ({ ...props }) => <li className="text-slate-100/90" {...props} />,
                    }}
                  >
                    {proj.achievements_md}
                  </ReactMarkdown>
                </div>
                {proj.technologies && proj.technologies.length ? (
                  <div className="mt-7 flex flex-wrap gap-3.5">
                    {proj.technologies.map((tech) => (
                      <span
                        key={tech}
                        className="rounded-full border border-emerald-400/40 bg-emerald-500/5 px-3.5 py-1 text-[11px] font-semibold text-emerald-100 shadow-[0_0_8px_rgba(0,255,200,0.12)]"
                      >
                        {tech}
                      </span>
                    ))}
                  </div>
                ) : null}
              </div>
            ))}
          </div>
        </div>

        <div className="flex justify-start">
          <Link
            href="/#experience"
            className="group/cta inline-flex items-center gap-2 rounded-full border border-[#00ffc3]/50 bg-black/50 px-4 py-2 text-sm font-medium text-accent transition-all duration-200 hover:border-[#00ffc3]/80 hover:text-accent hover:shadow-[0_0_14px_rgba(0,255,200,0.25)]"
          >
            <span
              aria-hidden="true"
              className="transition-transform duration-300 group-hover/cta:-translate-x-0.5"
            >
              &#8592;
            </span>
            <span>Назад к опыту</span>
          </Link>
        </div>
      </div>
    </Shell>
  );
}
