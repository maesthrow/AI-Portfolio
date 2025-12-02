import Section from "@/components/layout/Section";
import ExperienceCard from "@/components/experience/ExperienceCard";
import { ExperienceItem } from "@/lib/types";

type ExperienceSectionProps = {
  items: ExperienceItem[];
};

export default function ExperienceSection({ items }: ExperienceSectionProps) {
  const commercial = items.filter((item) => item.kind === "commercial");
  const sortedItems = [...commercial].sort((a, b) => {
    if (a.is_current !== b.is_current) return a.is_current ? -1 : 1;
    const aDate = a.start_date ? new Date(a.start_date).getTime() : 0;
    const bDate = b.start_date ? new Date(b.start_date).getTime() : 0;
    if (aDate !== bDate) return bDate - aDate;
    return (a.order_index ?? 0) - (b.order_index ?? 0);
  });

  return (
    <Section
      id="experience"
      label="Опыт"
      title="Коммерческий опыт"
      subtitle="Коммерческие проекты и компании: CV/LLM решения, RAG-системы и устойчивые backend-сервисы."
    >
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {sortedItems.map((item) => (
          <ExperienceCard key={item.id} item={item} />
        ))}
      </div>
    </Section>
  );
}
