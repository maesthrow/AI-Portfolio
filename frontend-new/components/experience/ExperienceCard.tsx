import { ExperienceItem } from "@/lib/types";

const kindMap: Record<ExperienceItem["kind"], { label: string; badge: string; tone: string }> = {
  current: { label: "ТЕКУЩЕЕ", badge: "NOW", tone: "text-accent-soft" },
  previous: { label: "ПРЕДЫДУЩЕЕ", badge: "PREV", tone: "text-slate-400" },
  founder: { label: "FOUNDER", badge: "FOUNDER", tone: "text-accent-alt" }
};

type ExperienceCardProps = {
  item: ExperienceItem;
};

export default function ExperienceCard({ item }: ExperienceCardProps) {
  const kind = kindMap[item.kind] || kindMap.current;
  return (
    <div className="group relative overflow-hidden rounded-3xl border border-[#00ffc3]/25 bg-gradient-to-br from-black/60 via-bg-panel/70 to-black/40 p-8 shadow-[0_0_25px_rgba(0,255,200,0.2)] transition-transform duration-300 hover:-translate-y-1 hover:scale-105 hover:border-[#00ffc3]/60 hover:shadow-[0_0_45px_rgba(0,255,200,0.35)]">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl border border-[#00ffc3]/35 bg-black/50 text-xs font-semibold shadow-[0_0_18px_rgba(0,255,200,0.2)]">
            {kind.badge}
          </div>
          <div>
            <p className={`text-xs font-semibold tracking-wide ${kind.tone}`}>{kind.label}</p>
            <p className="text-xl font-semibold text-slate-50">
              {item.role} - {item.company}
            </p>
            <p className="text-sm text-slate-400">{item.period}</p>
          </div>
        </div>
      </div>
      <p className="mt-4 text-[1.05rem] leading-relaxed text-gray-300">{item.description}</p>
      {item.companyUrl ? (
        <a
          className="mt-4 inline-flex items-center gap-2 text-sm font-semibold text-accent hover:text-accent-soft"
          href={item.companyUrl}
          target="_blank"
          rel="noreferrer"
        >
          Подробнее о компании
        </a>
      ) : null}
      <div className="pointer-events-none absolute inset-0 rounded-3xl border border-transparent transition-colors duration-300 group-hover:border-[#00ffc3]/50" />
    </div>
  );
}
