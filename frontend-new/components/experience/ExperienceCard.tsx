import Link from "next/link";
import { ExperienceItem } from "@/lib/types";

type ExperienceCardProps = {
  item: ExperienceItem;
};

function formatPeriod(start?: string | null, end?: string | null, isCurrent?: boolean) {
  if (!start) return null;
  const startYear = new Date(start).getFullYear();
  const endYear = end ? new Date(end).getFullYear() : null;
  if (isCurrent || (!end && !endYear)) return `${startYear} — н.в.`;
  if (endYear) return `${startYear} — ${endYear}`;
  return `${startYear}`;
}

export default function ExperienceCard({ item }: ExperienceCardProps) {
  const period = formatPeriod(item.start_date, item.end_date, item.is_current);
  const moreHref = `/experience/${item.company_slug}`;

  return (
    <div className="group relative h-full overflow-hidden rounded-3xl border border-[#00ffc3]/25 bg-gradient-to-br from-black/60 via-bg-panel/70 to-black/40 p-5 shadow-[0_0_15px_rgba(0,255,200,0.14)] transition duration-300 hover:border-[#00ffc3]/60 hover:shadow-[0_0_45px_rgba(0,255,200,0.35)] sm:p-6">
      <div className="absolute inset-px rounded-[22px] bg-gradient-to-r from-accent/10 via-transparent to-accent-alt/10 opacity-0 transition-opacity duration-500 group-hover:opacity-70" />
      <div className="relative flex h-full flex-col gap-3">
        <div className="flex flex-wrap items-center gap-2 text-[10px] font-semibold uppercase tracking-wide text-slate-200">
          <span
            className={`rounded-full px-2 py-0.5 ${
              item.is_current
                ? "border border-emerald-400/60 bg-emerald-400/10 text-emerald-200"
                : "border border-slate-600/70 bg-slate-800/70 text-slate-200"
            }`}
          >
            {item.is_current ? "Текущее" : "Прошлое"}
          </span>
        </div>

        <div>
          <h3 className="text-lg font-semibold text-slate-50 sm:text-xl">{item.role}</h3>
          <div className="mt-1 flex flex-wrap items-center gap-3 text-sm text-slate-300">
            {item.company_name ? (
              item.company_url ? (
                <a
                  href={item.company_url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-emerald-300 hover:text-emerald-200"
                >
                  {item.company_name}
                </a>
              ) : (
                <span className="text-emerald-300">{item.company_name}</span>
              )
            ) : null}
            {item.company_name && period ? <span className="text-slate-500">·</span> : null}
            {period ? <span className="text-slate-400">{period}</span> : null}
          </div>
        </div>

        {item.company_role_md ? (
          <p className="text-sm leading-relaxed text-slate-100/90">{item.company_role_md}</p>
        ) : item.company_summary_md ? (
          <p className="text-sm leading-relaxed text-slate-100/90">{item.company_summary_md}</p>
        ) : null}

        <div className="mt-auto flex justify-end border-t border-[#00ffc3]/20 pt-4">
          <Link
            href={moreHref}
            className="group/cta inline-flex items-center gap-1.5 rounded-full border border-[#00ffc3]/50 bg-black/50 px-4 py-1.5 text-xs font-semibold text-slate-200 transition-all duration-200 hover:border-[#00ffc3]/80 hover:text-accent hover:shadow-[0_0_14px_rgba(0,255,200,0.25)]"
          >
            Подробнее
            <span
              aria-hidden="true"
              className="transition-transform duration-300 group-hover/cta:translate-x-0.5"
            >
              →
            </span>
          </Link>
        </div>
      </div>
    </div>
  );
}
