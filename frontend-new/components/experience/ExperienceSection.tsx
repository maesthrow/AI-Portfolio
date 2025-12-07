import Section from "@/components/layout/Section";
import ExperienceCard from "@/components/experience/ExperienceCard";
import { sortExperience } from "@/lib/presentation";
import { ExperienceItem, SectionMeta } from "@/lib/types";

type ExperienceSectionProps = {
  items: ExperienceItem[];
  sectionMeta?: SectionMeta;
};

const defaultLabel = "КОММЕРЧЕСКИЙ ОПЫТ";
const defaultTitle = "Коммерческий опыт";
const defaultSubtitle =
  "Коммерческие проекты и компании: ML/LLM-направления, RAG-системы, надежные backend-сервисы и интеграции.";

export default function ExperienceSection({ items, sectionMeta }: ExperienceSectionProps) {
  const commercial = items.filter((item) => item.kind === "commercial");
  const sortedItems = sortExperience(commercial);

  return (
    <Section
      id="experience"
      label={defaultLabel}
      title={sectionMeta?.title || defaultTitle}
      subtitle={sectionMeta?.subtitle || defaultSubtitle}
    >
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {sortedItems.map((item) => (
          <ExperienceCard key={item.id} item={item} />
        ))}
      </div>
    </Section>
  );
}
