import Section from "@/components/layout/Section";
import StatsGrid from "@/components/about/StatsGrid";
import { Profile, StatItem } from "@/lib/types";

type AboutMeSectionProps = {
  profile: Profile;
  stats: StatItem[];
};

const sectionLabel = "ОБО МНЕ";
const sectionTitle = "Обо мне";
const aboutParagraph1 =
  "ML/LLM инженер с продуктовым подходом и бэкенд-фоном.";
const aboutParagraph2 =
  "Делаю AI-функциональность удобной и надежной: продумываю архитектуру, забочусь о качестве моделей и интегрирую ML-решения так, чтобы они помогали бизнесу.";
const bulletSections = [
  {
    title: "CV",
    items: [
      "Детекция и сегментация, пайплайны обработки изображений.",
      "Построение датасетов, аугментация, инструменты валидации.",
      "Запуск CV-сервисов в продакшен."
    ]
  },
  {
    title: "LLM / RAG",
    items: [
      "Fine-tunung моделей, векторные пайплайны.",
      "Агентные сценарии, инструментальные вызовы.",
      "Контроль качества ответов, настройка промптов, RAG-архитектуры под прод."
    ]
  },
  {
    title: "Backend / MLOps",
    items: [
      "Python, FastAPI, Celery, PostgreSQL, Redis, MLflow, Docker, vLLM.",
      "Интеграции с микросервисами и внешними API.",
      "Наблюдаемость: логирование, мониторинг, пайплайны обучения."
    ]
  }
];

export default function AboutMeSection({ profile: _profile, stats }: AboutMeSectionProps) {
  return (
    <Section id="about" label={sectionLabel} title={sectionTitle} className="mt-28 md:mt-20">
      <div className="grid gap-8 rounded-3xl border border-[#00ffc3]/20 bg-black/40 p-6 shadow-[0_0_25px_rgba(0,255,200,0.25)] backdrop-blur sm:p-8">
        <div className="space-y-4">
          <p className="max-w-3xl text-left text-lg leading-relaxed text-slate-100 md:max-w-4xl">
            {aboutParagraph1}
          </p>
          <p className="max-w-3xl text-left text-lg leading-relaxed text-slate-100 md:max-w-4xl">
            {aboutParagraph2}
          </p>
          <div className="grid gap-6 md:grid-cols-3">
            {bulletSections.map((section) => (
              <div
                key={section.title}
                className="group flex h-full flex-col rounded-3xl border border-[#00ffc3]/20 bg-gradient-to-br from-black/60 via-bg-panel/70 to-black/50 p-6 shadow-[0_0_25px_rgba(0,255,200,0.2)] transition-transform duration-300 hover:-translate-y-1 hover:scale-[1.02] hover:border-[#00ffc3]/60 hover:shadow-[0_0_45px_rgba(0,255,200,0.35)]"
              >
                <div className="flex items-center justify-between">
                  <h3 className="font-semibold text-accent-soft">{section.title}</h3>
                  <span className="rounded-full border border-[#00ffc3]/30 px-3 py-1 text-xs uppercase text-accent-soft/80">
                    focus
                  </span>
                </div>
                <ul className="mt-4 list-disc space-y-2 pl-5 text-left text-base leading-relaxed text-gray-300 marker:text-accent-soft">
                  {section.items.map((item) => (
                    <li key={item}>{item}</li>
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
