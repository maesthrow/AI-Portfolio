import Section from "@/components/layout/Section";
import { TechFocusItem } from "@/lib/types";

type TechFocusSectionProps = {
  items: TechFocusItem[];
};

export default function TechFocusSection({ items }: TechFocusSectionProps) {
  return (
    <Section
      id="tech"
      title="ТЕХНОЛОГИЧЕСКИЙ ФОКУС"
      subtitle="RAG/агенты, CV, .NET backend, MLOps и интеграции. Стек, с которым работаю чаще всего."
    >
      <div className="grid gap-4 md:grid-cols-2">
        {items.map((item) => (
          <div
            key={item.id}
            className="rounded-2xl border border-accent/30 bg-black/40 p-5 shadow-neon transition-transform duration-200 hover:-translate-y-1 hover:shadow-neon-strong"
          >
            <div className="flex items-center justify-between">
              <p className="font-mono text-sm text-accent-soft">{item.label}</p>
              <span className="text-xs uppercase text-accent/80">stack</span>
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              {item.tags.map((tag) => (
                <span
                  key={tag}
                  className="rounded-full border border-accent/40 bg-accent/10 px-3 py-1 text-xs text-slate-100"
                >
                  {tag}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </Section>
  );
}
