import { ExperienceItem } from "@/lib/types";

type ExperienceCardProps = {
  item: ExperienceItem;
};

function formatYear(value?: string | null) {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return date.getFullYear().toString();
}

function buildPeriod(item: ExperienceItem) {
  const start = formatYear(item.start_date);
  const end = formatYear(item.end_date);
  if (start && item.is_current) return `${start} — н.в.`;
  if (start && end) return `${start} — ${end}`;
  if (start) return start;
  return (item as any).period || null;
}

function extractBullets(md?: string | null) {
  if (!md) return [];
  return md
    .split("\n")
    .map((line) => line.replace(/^[*-]\s*/, "").trim())
    .filter(Boolean)
    .slice(0, 4);
}

export default function ExperienceCard({ item }: ExperienceCardProps) {
  const companyName = item.company_name || (item as any).company || "";
  const companyUrl = item.company_url || (item as any).companyUrl || null;
  const period = buildPeriod(item);
  const bullets = extractBullets(item.description_md || (item as any).description);
  const hasCompany = Boolean(companyName);
  const kindLabel = item.kind ? item.kind.replace(/_/g, " ").toUpperCase() : null;

  return (
    <div className="group relative overflow-hidden rounded-3xl border border-[#00ffc3]/25 bg-gradient-to-br from-black/60 via-bg-panel/70 to-black/40 p-8 shadow-[0_0_25px_rgba(0,255,200,0.2)] transition-transform duration-300 hover:-translate-y-1.5 hover:scale-[1.02] hover:border-[#00ffc3]/60 hover:shadow-[0_0_45px_rgba(0,255,200,0.35)]">
      <div className="absolute inset-px rounded-[22px] bg-gradient-to-r from-accent/10 via-transparent to-accent-alt/10 opacity-0 transition-opacity duration-500 group-hover:opacity-70" />
      <div className="relative flex flex-col gap-4">
        <div className="flex flex-wrap items-start gap-3">
          <span
            className={`rounded-full border px-3 py-1 text-xs font-semibold tracking-wide shadow-[0_0_14px_rgba(0,255,200,0.28)] ${
              item.is_current
                ? "border-accent/60 bg-accent/15 text-accent-soft"
                : "border-slate-700/70 bg-slate-900/70 text-slate-200"
            }`}
          >
            {item.is_current ? "ТЕКУЩЕЕ" : "ПРОШЛОЕ"}
          </span>
          {kindLabel ? (
            <span className="rounded-full border border-slate-800 bg-black/50 px-3 py-1 text-[11px] uppercase tracking-wide text-slate-300">
              {kindLabel}
            </span>
          ) : null}
        </div>

        <div className="space-y-2">
          <p className="text-2xl font-semibold leading-tight text-slate-50">{item.role}</p>
          <div className="flex flex-wrap items-center gap-2 text-sm text-slate-300">
            {hasCompany ? (
              companyUrl ? (
                <a
                  href={companyUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-2 text-accent hover:text-accent-soft"
                >
                  <span className="h-1.5 w-1.5 rounded-full bg-accent-soft shadow-[0_0_8px_rgba(0,255,200,0.35)]" />
                  {companyName}
                </a>
              ) : (
                <span className="inline-flex items-center gap-2">
                  <span className="h-1.5 w-1.5 rounded-full bg-accent-soft shadow-[0_0_8px_rgba(0,255,200,0.35)]" />
                  {companyName}
                </span>
              )
            ) : null}
            {hasCompany && period ? <span className="text-slate-500">•</span> : null}
            {period ? <span className="text-slate-400">{period}</span> : null}
          </div>
        </div>

        {bullets.length ? (
          <ul className="space-y-2 text-sm leading-relaxed text-slate-300">
            {bullets.map((line) => (
              <li key={line} className="flex items-start gap-3">
                <span className="mt-1 h-2 w-2 rounded-full bg-accent-soft shadow-[0_0_8px_rgba(0,255,200,0.35)]" />
                <span className="flex-1">{line}</span>
              </li>
            ))}
          </ul>
        ) : null}
      </div>
    </div>
  );
}
