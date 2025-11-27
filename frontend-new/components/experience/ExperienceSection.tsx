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
      title="ОПЫТ РАБОТЫ"
      subtitle="Опыт доставки CV/LLM сервисов и backend-платформ до продакшена."
    >
      <div className="grid gap-5">
        {items.map((item) => (
          <ExperienceCard key={item.id} item={item} />
        ))}
      </div>
    </Section>
  );
}
