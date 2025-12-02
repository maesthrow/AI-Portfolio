import { ExperienceItem } from "@/lib/types";

type ExperienceCardProps = {
  item: ExperienceItem;
};

function formatPeriod(start?: string | null, end?: string | null, isCurrent?: boolean) {
  if (!start) return null;
  const startDate = new Date(start);
  const startYear = Number.isNaN(startDate.getTime()) ? null : startDate.getFullYear();
  const endDate = end ? new Date(end) : null;
  const endYear = endDate && !Number.isNaN(endDate.getTime()) ? endDate.getFullYear() : null;

  if (!startYear) return null;
  if (isCurrent) return `${startYear} — н.в.`;
  if (endYear) return `${startYear} — ${endYear}`;
  return `${startYear}`;
}

function parseBullets(md?: string | null) {
  if (!md) return [];
  return md
    .split("\n")
    .map((line) => line.replace(/^[*-]\s*/, "").trim())
    .filter(Boolean);
}

function renderCompanyAndProject(exp: ExperienceItem) {
  const company = exp.company_name
    ? exp.company_url
      ? (
          <a href={exp.company_url} target="_blank" rel="noreferrer" className="hover:text-emerald-300">
            {exp.company_name}
          </a>
        )
      : exp.company_name
    : null;

  const project = exp.project_name
    ? exp.project_url || exp.project_slug
      ? (
          <a
            href={exp.project_url || `/projects/${exp.project_slug}`}
            target="_blank"
            rel="noreferrer"
            className="hover:text-emerald-300"
          >
            {exp.project_name}
          </a>
        )
      : exp.project_name
    : null;

  if (company && project) {
    return (
      <>
        {company} · {project}
      </>
    );
  }
  return company || project || null;
}

export default function ExperienceCard({ item }: ExperienceCardProps) {
  const achievements = parseBullets(item.achievements_md);
  const legacyBullets = parseBullets(item.description_md);
  const bullets = achievements.length ? achievements : legacyBullets;
  const legacyFallbackText =
    !item.summary_md && !achievements.length && !legacyBullets.length ? item.description_md : null;
  const period = formatPeriod(item.start_date, item.end_date, item.is_current);

  return (
    <div className="group relative overflow-hidden rounded-3xl border border-[#00ffc3]/25 bg-gradient-to-br from-black/60 via-bg-panel/70 to-black/40 p-5 shadow-[0_0_25px_rgba(0,255,200,0.2)] transition-transform duration-300 hover:-translate-y-1.5 hover:scale-[1.02] hover:border-[#00ffc3]/60 hover:shadow-[0_0_45px_rgba(0,255,200,0.35)] sm:p-6">
      <div className="absolute inset-px rounded-[22px] bg-gradient-to-r from-accent/10 via-transparent to-accent-alt/10 opacity-0 transition-opacity duration-500 group-hover:opacity-70" />
      <div className="relative flex flex-col">
        <div className="flex flex-wrap items-center gap-2 text-[10px] font-semibold uppercase tracking-wide text-slate-200">
          <span
            className={`rounded-full px-2 py-0.5 ${
              item.is_current
                ? "border border-emerald-400/60 bg-emerald-400/10 text-emerald-200"
                : "border border-slate-600/70 bg-slate-800/70 text-slate-200"
            }`}
          >
            {item.is_current ? "текущее" : "прошлое"}
          </span>
          <span
            className={`rounded-full px-2 py-0.5 ${
              item.kind === "personal"
                ? "border border-purple-400/70 bg-purple-500/15 text-slate-200"
                : "border border-slate-500/70 bg-slate-700/40 text-slate-200"
            }`}
          >
            {item.kind === "commercial" ? "commercial" : "personal"}
          </span>
        </div>

        <h3 className="mt-3 text-lg font-semibold text-slate-50 sm:text-xl">{item.role}</h3>

        <p className="mt-1 text-sm text-slate-300">{renderCompanyAndProject(item)}</p>

        {period ? <p className="mt-1 text-xs text-slate-500">{period}</p> : null}

        {item.summary_md ? (
          <div className="mt-4 text-sm leading-relaxed text-slate-100">
            <p>{item.summary_md}</p>
          </div>
        ) : null}

        {bullets.length ? (
          <ul className="mt-3 ml-4 list-disc space-y-1 text-sm text-slate-200 marker:text-emerald-300">
            {bullets.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        ) : null}

        {legacyFallbackText ? (
          <p className="mt-3 text-sm text-slate-200">
            {/* Legacy description_md fallback; remove after data fully migrated */}
            {legacyFallbackText}
          </p>
        ) : null}
      </div>
    </div>
  );
}
