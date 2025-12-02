import Section from "@/components/layout/Section";
import ExperienceCard from "@/components/experience/ExperienceCard";
import { ExperienceItem } from "@/lib/types";

type ExperienceSectionProps = {
  items: ExperienceItem[];
};

export default function ExperienceSection({ items }: ExperienceSectionProps) {
  const sortedItems = [...items].sort((a, b) => {
    const kindOrder = (val: ExperienceItem["kind"]) => {
      if (val === "commercial") return 0;
      if (val === "personal") return 1;
      return 2; // любые прочие в конец
    };

    // 1) коммерческие выше личных
    const kindDiff = kindOrder(a.kind) - kindOrder(b.kind);
    if (kindDiff !== 0) return kindDiff;

    // 2) текущие выше прошлых
    if (a.is_current !== b.is_current) return a.is_current ? -1 : 1;

    // 3) более новые даты выше
    const aDate = a.start_date ? new Date(a.start_date).getTime() : 0;
    const bDate = b.start_date ? new Date(b.start_date).getTime() : 0;
    if (aDate !== bDate) return bDate - aDate;

    // 4) запасной порядок по order_index (большее выше)
    return (b.order_index ?? 0) - (a.order_index ?? 0);
  });

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
