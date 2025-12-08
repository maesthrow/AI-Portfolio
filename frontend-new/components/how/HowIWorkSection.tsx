import Section from "@/components/layout/Section";
import { SectionMeta, WorkApproach } from "@/lib/types";
import { Lightbulb, Blocks, Rocket, LucideIcon } from "lucide-react";

type HowIWorkSectionProps = {
  workApproaches?: WorkApproach[];
  sectionMeta?: SectionMeta;
};

const iconMap: Record<string, LucideIcon> = {
  lightbulb: Lightbulb,
  blocks: Blocks,
  rocket: Rocket,
};

// Fallback content
const fallbackItems = [
  {
    title: "Product-first дизайн AI",
    icon: "lightbulb",
    bullets: [
      "Формулирую use-case'ы для CV, LLM/RAG и ML-фич на языке бизнеса.",
      "Веду эксперименты, опираюсь на метрики и быструю проверку гипотез.",
      "Делаю релизы в AI-цикле: модель, пайплайн, мониторинг и обратная связь."
    ]
  },
  {
    title: "Архитектура и интеграции",
    icon: "blocks",
    bullets: [
      "Проектирую API, сборку и оркестрацию пайплайнов под продуктовые SLA.",
      "Оптимизирую RAG/CV: поиск, сжатие, память, стабильность отклика.",
      "Наблюдаемость: логирование, метрики качества, деградации, алерты."
    ]
  },
  {
    title: "Запуск и поддержка",
    icon: "rocket",
    bullets: [
      "CI/CD, feature flags и канарейки, чтобы релизы были безопасными.",
      "Работаю с нагрузкой: буферы, backpressure, деградационные режимы.",
      "Синхронизируюсь с dev/data/infra-командами, чтобы стек работал вместе."
    ]
  }
];

const defaultLabel = "КАК Я РАБОТАЮ С AI";
const defaultTitle = "Как я работаю с AI-продуктами";
const defaultSubtitle =
  "Подход к RAG, CV и ML-системам с продуктовой ориентацией и предсказуемым запуском.";

export default function HowIWorkSection({
  workApproaches = [],
  sectionMeta
}: HowIWorkSectionProps) {
  // Use API data if available, otherwise use fallback
  const items =
    workApproaches.length > 0
      ? workApproaches.map((wa) => ({
          title: wa.title,
          icon: wa.icon || null,
          bullets: wa.bullets.map((b) => b.text)
        }))
      : fallbackItems;

  const label = defaultLabel;
  const title = sectionMeta?.title || defaultTitle;
  const subtitle = sectionMeta?.subtitle || defaultSubtitle;

  return (
    <Section id="how-i-work" label={label} title={title} subtitle={subtitle}>
      <div className="grid gap-8 md:grid-cols-2 xl:grid-cols-3">
        {items.map((item) => {
          const Icon = item.icon ? iconMap[item.icon] : null;

          return (
            <div
              key={item.title}
              className="group rounded-3xl border border-[#00ffc3]/25 bg-gradient-to-br from-accent/10 via-bg-panel to-black/50 p-8 shadow-[0_0_15px_rgba(0,255,200,0.14)] transition duration-300 hover:border-[#00ffc3]/60 hover:shadow-[0_0_45px_rgba(0,255,200,0.35)]"
            >
              {/* Header with icon */}
              <div className="flex items-center gap-3">
                {Icon && (
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-[#00ffc3]/30 bg-[#00ffc3]/10">
                    <Icon className="h-5 w-5 text-[#00ffc3]" />
                  </div>
                )}
                <p className="font-mono text-sm text-accent-soft"># {item.title}</p>
              </div>

              {/* Bullets with cyber glow */}
              <ul className="mt-5 space-y-3 text-[1.05rem] leading-relaxed text-gray-300">
                {item.bullets.map((b, idx) => (
                  <li key={idx} className="flex items-start gap-3">
                    <span className="mt-2 h-1.5 w-1.5 min-w-[6px] rounded-full bg-[#00ffc3] shadow-[0_0_6px_rgba(0,255,195,0.6),0_0_12px_rgba(0,255,195,0.3)]" />
                    <span>{b}</span>
                  </li>
                ))}
              </ul>
            </div>
          );
        })}
      </div>
    </Section>
  );
}
