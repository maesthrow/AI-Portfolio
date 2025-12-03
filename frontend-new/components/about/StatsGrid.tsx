 "use client";

import { useEffect, useRef, useState } from "react";
import { StatItem } from "@/lib/types";

function CountUp({ value }: { value: string | number }) {
  const targetText = String(value);
  const match = targetText.match(/(-?\d+(?:\.\d+)?)/);
  if (!match) return <>{targetText}</>;

  const numberPart = parseFloat(match[1]);
  const prefix = targetText.slice(0, match.index ?? 0);
  const suffix = targetText.slice((match.index ?? 0) + match[1].length);

  const [display, setDisplay] = useState(0);
  const hasAnimated = useRef(false);
  const ref = useRef<HTMLSpanElement | null>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting && !hasAnimated.current) {
            hasAnimated.current = true;
            const duration = 1200;
            const start = performance.now();
            const step = (now: number) => {
              const progress = Math.min((now - start) / duration, 1);
              const eased = 1 - Math.pow(1 - progress, 3);
              const current = numberPart * eased;
              setDisplay(current);
              if (progress < 1) requestAnimationFrame(step);
            };
            requestAnimationFrame(step);
          }
        });
      },
      { threshold: 0.4 }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [numberPart]);

  const formatted = Math.round(display).toString();

  return (
    <span ref={ref}>
      {prefix}
      {formatted}
      {suffix}
    </span>
  );
}

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
          <p className="mt-3 text-4xl font-semibold text-slate-50">
            <CountUp value={stat.value} />
          </p>
          {stat.hint ? (
            <p className="mt-2 text-sm leading-relaxed text-gray-300">{stat.hint}</p>
          ) : null}
        </div>
      ))}
    </div>
  );
}
