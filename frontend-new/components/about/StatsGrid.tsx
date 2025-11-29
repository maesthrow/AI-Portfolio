import { StatItem } from "@/lib/types";

type StatsGridProps = {
  stats: StatItem[];
};

export default function StatsGrid({ stats }: StatsGridProps) {
  if (!stats?.length) return null;
  return (
    <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-3">
      {stats.map((stat) => (
        <div
          key={stat.id}
          className="group rounded-3xl border border-[#00ffc3]/20 bg-gradient-to-br from-black/60 via-bg-panel/70 to-black/50 p-8 shadow-[0_0_25px_rgba(0,255,200,0.2)] transition-transform duration-300 hover:-translate-y-1 hover:scale-105 hover:border-[#00ffc3]/60 hover:shadow-[0_0_45px_rgba(0,255,200,0.35)]"
        >
          <p className="text-sm uppercase tracking-wide text-accent-soft">{stat.label}</p>
          <p className="mt-3 text-4xl font-semibold text-slate-50">{stat.value}</p>
          {stat.hint ? (
            <p className="mt-2 text-sm leading-relaxed text-gray-300">{stat.hint}</p>
          ) : null}
        </div>
      ))}
    </div>
  );
}
