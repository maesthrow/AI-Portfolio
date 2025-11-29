import Section from "@/components/layout/Section";
import ExperienceCard from "@/components/experience/ExperienceCard";
import { ExperienceItem } from "@/lib/types";

type ExperienceSectionProps = {
  items: ExperienceItem[];
};

export default function ExperienceSection({ items }: ExperienceSectionProps) {
  return (
    <Section
      id="experience"
      title="Опыт"
      subtitle="Релевантные роли и проекты в CV/LLM-направлении и надёжных backend-системах."
    >
      <div className="grid gap-8">
        {items.map((item) => (
          <ExperienceCard key={item.id} item={item} />
        ))}
      </div>
    </Section>
  );
}
