import { ExperienceItem } from "@/lib/types";

const kindMap: Record<ExperienceItem["kind"], { label: string; emoji: string; tone: string }> = {
  current: { label: "CURRENT", emoji: "🚀", tone: "text-accent-soft" },
  previous: { label: "PREVIOUS", emoji: "💼", tone: "text-slate-400" },
  founder: { label: "FOUNDER", emoji: "🛠️", tone: "text-accent-alt" }
};

type ExperienceCardProps = {
  item: ExperienceItem;
};

export default function ExperienceCard({ item }: ExperienceCardProps) {
  const kind = kindMap[item.kind] || kindMap.current;
  return (
    <div className="relative overflow-hidden rounded-2xl border border-slate-700/60 bg-gradient-to-br from-black/50 via-bg-panel/70 to-black/30 p-5 shadow-lg transition-transform duration-200 hover:-translate-y-1 hover:shadow-neon">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-accent/40 bg-black/50 text-xl">
            {kind.emoji}
          </div>
          <div>
            <p className={`text-xs font-semibold tracking-wide ${kind.tone}`}>{kind.label}</p>
            <p className="text-lg font-semibold text-slate-50">
              {item.role} — {item.company}
            </p>
            <p className="text-sm text-slate-400">{item.period}</p>
          </div>
        </div>
      </div>
      <p className="mt-3 text-sm leading-relaxed text-slate-200">{item.description}</p>
      {item.companyUrl ? (
        <a
          className="mt-3 inline-flex items-center gap-2 text-sm font-medium text-accent hover:text-accent-soft"
          href={item.companyUrl}
          target="_blank"
          rel="noreferrer"
        >
          Компания →
        </a>
      ) : null}
      <div className="pointer-events-none absolute inset-0 rounded-2xl border border-transparent transition-colors duration-200 hover:border-accent/40" />
    </div>
  );
}
