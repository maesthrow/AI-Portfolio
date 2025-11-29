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
      title="Публикации и выступления"
      subtitle="Подборка статей и публичных материалов по ML/LLM."
    >
      <div className="grid gap-8 md:grid-cols-2">
        {items.map((pub) => (
          <PublicationCard key={pub.id} publication={pub} />
        ))}
      </div>
    </Section>
  );
}
