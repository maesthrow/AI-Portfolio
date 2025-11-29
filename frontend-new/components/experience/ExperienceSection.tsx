import Section from "@/components/layout/Section";
import ExperienceCard from "@/components/experience/ExperienceCard";
import { ExperienceItem } from "@/lib/types";

type ExperienceSectionProps = {
  items: ExperienceItem[];
};

export default function ExperienceSection({ items }: ExperienceSectionProps) {
  const sortedItems = [...items].sort(
    (a, b) => (b.order_index ?? 0) - (a.order_index ?? 0)
  );

  return (
    <Section
      id="experience"
      label="ОПЫТ"
      title="Опыт"
      subtitle="Продуктовые роли и лид в CV/LLM-направлениях с сильным фокусом на backend-системы."
    >
      <div className="grid gap-8">
        {sortedItems.map((item) => (
          <ExperienceCard key={item.id} item={item} />
        ))}
      </div>
    </Section>
  );
}
