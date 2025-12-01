import Section from "@/components/layout/Section";
import { TechFocusItem } from "@/lib/types";

type TechFocusSectionProps = {
  items: TechFocusItem[];
};

function normalizeTag(tag: TechFocusItem["tags"][number]) {
  if (typeof tag === "string") return tag;
  if (tag?.name) return tag.name;
  if (tag?.id !== undefined) return String(tag.id);
  return "tag";
}

export default function TechFocusSection({ items }: TechFocusSectionProps) {
  return (
    <Section
      id="tech"
      label="ТЕХНОЛОГИЧЕСКИЙ ФОКУС"
      title="Технологический фокус"
      subtitle="LLM, RAG, CV, backend и MLOps с упором на продуктовую надежность и гибкость решений."
    >
      <div className="grid gap-8 md:grid-cols-2">
        {items.map((item) => (
          <div
            key={item.id}
            className="group rounded-3xl border border-[#00ffc3]/25 bg-gradient-to-br from-black/60 via-bg-panel/80 to-black/50 p-8 shadow-[0_0_25px_rgba(0,255,200,0.2)] transition-transform duration-300 hover:-translate-y-1 hover:scale-[1.02] hover:border-[#00ffc3]/60 hover:shadow-[0_0_45px_rgba(0,255,200,0.35)]"
          >
            <div className="flex items-center justify-between">
              <p className="font-mono text-sm text-accent-soft">{item.label}</p>
              <span className="rounded-full border border-[#00ffc3]/40 px-3 py-1 text-xs uppercase text-accent/80">
                stack
              </span>
            </div>
            <div className="mt-5 flex flex-wrap gap-3">
              {item.tags.map((tag) => (
                <span
                  key={normalizeTag(tag)}
                  className="rounded-full border border-[#00ffc3]/40 bg-accent/10 px-3 py-1 text-xs text-slate-100 shadow-[0_0_8px_rgba(0,255,200,0.25)]"
                >
                  {normalizeTag(tag)}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </Section>
  );
}
