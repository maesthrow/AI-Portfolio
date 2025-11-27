import { StatItem } from "@/lib/types";

type StatsGridProps = {
  stats: StatItem[];
};

export default function StatsGrid({ stats }: StatsGridProps) {
  if (!stats?.length) return null;
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {stats.map((stat) => (
        <div
          key={stat.id}
          className="rounded-2xl border border-accent/30 bg-black/40 p-4 shadow-inner shadow-accent/10 transition-transform duration-200 hover:-translate-y-1 hover:shadow-neon"
        >
          <p className="text-sm uppercase tracking-wide text-accent-soft">{stat.label}</p>
          <p className="mt-2 text-3xl font-semibold text-slate-50">{stat.value}</p>
          {stat.hint ? <p className="mt-1 text-xs text-slate-400">{stat.hint}</p> : null}
        </div>
      ))}
    </div>
  );
}
