import Section from "@/components/layout/Section";
import StatsGrid from "@/components/about/StatsGrid";
import { FocusArea, Profile, StatItem } from "@/lib/types";

type AboutMeSectionProps = {
  profile: Profile;
  stats: StatItem[];
  focusAreas?: FocusArea[];
};

const sectionLabel = "ОБО МНЕ";
const sectionTitle = "Обо мне";

// Fallback content if API data is not available
const fallbackParagraph1 = "ML/LLM инженер с продуктовым подходом и бэкенд-фоном.";
const fallbackParagraph2 =
  "Делаю AI-функциональность удобной и надежной: продумываю архитектуру, забочусь о качестве моделей и интегрирую ML-решения так, чтобы они помогали бизнесу.";
const fallbackBulletSections = [
  {
    title: "CV",
    is_primary: false,
    items: [
      "Детекция и сегментация, пайплайны обработки изображений.",
      "Построение датасетов, аугментация, инструменты валидации.",
      "Запуск CV-сервисов в продакшен."
    ]
  },
  {
    title: "LLM / RAG",
    is_primary: true,
    items: [
      "Fine-tunung моделей, векторные пайплайны.",
      "Агентные сценарии, инструментальные вызовы.",
      "Контроль качества ответов, настройка промптов, RAG-архитектуры под прод."
    ]
  },
  {
    title: "Backend / MLOps",
    is_primary: false,
    items: [
      "Python, FastAPI, Celery, PostgreSQL, Redis, MLflow, Docker, vLLM.",
      "Интеграции с микросервисами и внешними API.",
      "Наблюдаемость: логирование, мониторинг, пайплайны обучения."
    ]
  }
];

export default function AboutMeSection({ profile, stats, focusAreas = [] }: AboutMeSectionProps) {
  // Use API data if available, otherwise use fallback
  const sections =
    focusAreas.length > 0
      ? focusAreas.map((fa) => ({
          title: fa.title,
          is_primary: fa.is_primary,
          items: fa.bullets.map((b) => b.text)
        }))
      : fallbackBulletSections;

  // Get summary from profile if available
  const summaryText = (profile as any).summary_md || null;
  const paragraph1 = summaryText ? summaryText.split(".")[0] + "." : fallbackParagraph1;
  const paragraph2 = summaryText
    ? summaryText.split(".").slice(1).join(".").trim()
    : fallbackParagraph2;

  return (
    <Section id="about" label={sectionLabel} title={sectionTitle} className="mt-28 md:mt-20">
      <div className="grid gap-8 rounded-3xl border border-[#00ffc3]/20 bg-black/40 p-6 shadow-[0_0_15px_rgba(0,255,200,0.16)] backdrop-blur sm:p-8">
        <div className="space-y-4">
          <p className="max-w-3xl text-left text-lg leading-relaxed text-slate-100 md:max-w-4xl">
            {paragraph1}
          </p>
          {paragraph2 && (
            <p className="max-w-3xl text-left text-lg leading-relaxed text-slate-100 md:max-w-4xl">
              {paragraph2}
            </p>
          )}
          <div className="grid gap-6 md:grid-cols-3">
            {sections.map((section) => (
              <div
                key={section.title}
                className="group flex h-full flex-col rounded-3xl border border-[#00ffc3]/20 bg-gradient-to-br from-black/60 via-bg-panel/70 to-black/50 p-6 shadow-[0_0_15px_rgba(0,255,200,0.14)] transition duration-300 hover:border-[#00ffc3]/60 hover:shadow-[0_0_45px_rgba(0,255,200,0.35)]"
              >
                <div className="flex items-center justify-between">
                  <h3 className="font-semibold text-accent-soft">{section.title}</h3>
                  {section.is_primary && (
                    <span className="rounded-full border border-[#00ffc3]/30 px-3 py-1 text-xs uppercase text-accent-soft/80">
                      focus
                    </span>
                  )}
                </div>
                <ul className="mt-4 list-disc space-y-2 pl-5 text-left text-base leading-relaxed text-gray-300 marker:text-accent-soft">
                  {section.items.map((item, idx) => (
                    <li key={idx}>{item}</li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
        <StatsGrid stats={stats} />
      </div>
    </Section>
  );
}
