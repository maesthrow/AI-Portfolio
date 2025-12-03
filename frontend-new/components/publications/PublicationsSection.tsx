import Section from "@/components/layout/Section";
import PublicationCard from "@/components/publications/PublicationCard";
import { Publication } from "@/lib/types";

type PublicationsSectionProps = {
  items: Publication[];
};

export default function PublicationsSection({ items }: PublicationsSectionProps) {
  if (!items?.length) return null;
  return (
    <Section
      id="publications"
      label="КОНТЕНТ И ПУБЛИКАЦИИ"
      title="Публикации и выступления"
      subtitle="Выжимки опыта и заметки по ML/LLM."
    >
      <div className="grid gap-8 md:grid-cols-2">
        {items.map((pub) => (
          <PublicationCard key={pub.id} publication={pub} />
        ))}
      </div>
    </Section>
  );
}
