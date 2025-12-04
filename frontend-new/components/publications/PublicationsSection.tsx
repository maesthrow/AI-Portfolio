import Section from "@/components/layout/Section";
import PublicationCard from "@/components/publications/PublicationCard";
import { Publication, SectionMeta } from "@/lib/types";

type PublicationsSectionProps = {
  items: Publication[];
  sectionMeta?: SectionMeta;
};

const defaultLabel = "КОНТЕНТ И ПУБЛИКАЦИИ";
const defaultTitle = "Публикации и выступления";
const defaultSubtitle = "Выжимки опыта и заметки по ML/LLM.";

export default function PublicationsSection({ items, sectionMeta }: PublicationsSectionProps) {
  if (!items?.length) return null;
  return (
    <Section
      id="publications"
      label={defaultLabel}
      title={sectionMeta?.title || defaultTitle}
      subtitle={sectionMeta?.subtitle || defaultSubtitle}
    >
      <div className="grid gap-8 md:grid-cols-2">
        {items.map((pub) => (
          <PublicationCard key={pub.id} publication={pub} />
        ))}
      </div>
    </Section>
  );
}
