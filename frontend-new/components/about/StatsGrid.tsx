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
    <div
      className={
        "grid gap-8 sm:grid-cols-2 lg:grid-cols-3 " +
        // 2-col: center lone last when total is odd (3, 5, 7…)
        "sm:[&>*:last-child:nth-child(odd)]:col-span-2 sm:[&>*:last-child:nth-child(odd)]:mx-auto sm:[&>*:last-child:nth-child(odd)]:w-[calc(50%-1rem)] " +
        // 3-col: reset md rule (lone-in-2-col differs from lone-in-3-col)
        "lg:[&>*:last-child:nth-child(odd)]:col-span-1 lg:[&>*:last-child:nth-child(odd)]:mx-0 lg:[&>*:last-child:nth-child(odd)]:w-auto " +
        // 3-col: center lone last when total = 3n+1 (4, 7, 10…)
        "lg:[&>*:last-child:nth-child(3n+1)]:col-span-3 lg:[&>*:last-child:nth-child(3n+1)]:mx-auto lg:[&>*:last-child:nth-child(3n+1)]:w-[calc(33.333%-1.333rem)]"
      }
    >
      {stats.map((stat) => (
        <div
          key={stat.id}
          className="group rounded-3xl border border-[#00ffc3]/20 bg-gradient-to-br from-black/60 via-bg-panel/70 to-black/50 p-8 shadow-[0_0_15px_rgba(0,255,200,0.14)] transition duration-300 hover:border-[#00ffc3]/60 hover:shadow-[0_0_45px_rgba(0,255,200,0.35)]"
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
