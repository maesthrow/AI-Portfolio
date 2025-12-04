import Section from "@/components/layout/Section";
import { SectionMeta, WorkApproach } from "@/lib/types";

type HowIWorkSectionProps = {
  workApproaches?: WorkApproach[];
  sectionMeta?: SectionMeta;
};

// Fallback content
const fallbackItems = [
  {
    title: "Product-first дизайн AI",
    bullets: [
      "Формулирую use-case'ы для CV, LLM/RAG и ML-фич на языке бизнеса.",
      "Веду эксперименты, опираюсь на метрики и быструю проверку гипотез.",
      "Делаю релизы в AI-цикле: модель, пайплайн, мониторинг и обратная связь."
    ]
  },
  {
    title: "Архитектура и интеграции",
    bullets: [
      "Проектирую API, сборку и оркестрацию пайплайнов под продуктовые SLA.",
      "Оптимизирую RAG/CV: поиск, сжатие, память, стабильность отклика.",
      "Наблюдаемость: логирование, метрики качества, деградации, алерты."
    ]
  },
  {
    title: "Запуск и поддержка",
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
          bullets: wa.bullets.map((b) => b.text)
        }))
      : fallbackItems;

  const label = defaultLabel;
  const title = sectionMeta?.title || defaultTitle;
  const subtitle = sectionMeta?.subtitle || defaultSubtitle;

  return (
    <Section id="how-i-work" label={label} title={title} subtitle={subtitle}>
      <div className="grid gap-8 md:grid-cols-2 xl:grid-cols-3">
        {items.map((item) => (
          <div
            key={item.title}
            className="group rounded-3xl border border-[#00ffc3]/25 bg-gradient-to-br from-accent/10 via-bg-panel to-black/50 p-8 shadow-[0_0_15px_rgba(0,255,200,0.14)] transition duration-300 hover:border-[#00ffc3]/60 hover:shadow-[0_0_45px_rgba(0,255,200,0.35)]"
          >
            <p className="font-mono text-sm text-accent-soft"># {item.title}</p>
            <ul className="mt-4 space-y-3 text-[1.05rem] leading-relaxed text-gray-300">
              {item.bullets.map((b, idx) => (
                <li key={idx} className="flex items-start gap-3">
                  <span className="mt-1 h-2 w-2 rounded-full bg-accent-soft shadow-[0_0_8px_rgba(0,255,200,0.35)]" />
                  <span>{b}</span>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </Section>
  );
}
