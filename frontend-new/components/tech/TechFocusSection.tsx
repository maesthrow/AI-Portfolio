import Section from "@/components/layout/Section";
import { SectionMeta, TechFocusItem } from "@/lib/types";
import TechTag from "@/components/ui/TechTag";

type TechFocusSectionProps = {
  items: TechFocusItem[];
  sectionMeta?: SectionMeta;
};

const defaultLabel = "ТЕХНОЛОГИЧЕСКИЙ ФОКУС";
const defaultTitle = "Технологический фокус";
const defaultSubtitle =
  "LLM, RAG, CV, backend и MLOps с упором на продуктовую надежность и гибкость решений.";

function normalizeTag(tag: TechFocusItem["tags"][number]) {
  if (typeof tag === "string") return tag;
  if (tag?.name) return tag.name;
  if (tag?.id !== undefined) return String(tag.id);
  return "tag";
}

export default function TechFocusSection({ items, sectionMeta }: TechFocusSectionProps) {
  return (
    <Section
      id="tech"
      label={defaultLabel}
      title={sectionMeta?.title || defaultTitle}
      subtitle={sectionMeta?.subtitle || defaultSubtitle}
    >
      <div className="grid gap-8 md:grid-cols-2">
        {items.map((item) => (
          <div
            key={item.id}
            className="group rounded-3xl border border-[#00ffc3]/25 bg-gradient-to-br from-black/60 via-bg-panel/80 to-black/50 p-8 shadow-[0_0_15px_rgba(0,255,200,0.14)] transition duration-300 hover:border-[#00ffc3]/60 hover:shadow-[0_0_45px_rgba(0,255,200,0.35)]"
          >
            <div className="flex items-center justify-between">
              <p className="font-mono text-sm text-accent-soft">{item.label}</p>
              <span className="rounded-full border border-[#00ffc3]/40 px-3 py-1 text-xs uppercase text-accent/80">
                stack
              </span>
            </div>
            <div className="mt-5 flex flex-wrap gap-3">
              {item.tags.map((tag) => (
                <TechTag key={normalizeTag(tag)} variant="stack">
                  {normalizeTag(tag)}
                </TechTag>
              ))}
            </div>
          </div>
        ))}
      </div>
    </Section>
  );
}
