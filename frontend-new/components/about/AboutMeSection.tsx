import Section from "@/components/layout/Section";
import StatsGrid from "@/components/about/StatsGrid";
import { FocusArea, Profile, StatItem } from "@/lib/types";

type AboutMeSectionProps = {
  profile: Profile;
  stats: StatItem[];
  focusAreas?: FocusArea[];
};

type AboutSection = {
  title: string;
  is_primary: boolean;
  items: string[];
  badge?: string;
};

const sectionLabel = "ОБО МНЕ";
const sectionTitle = "ОБО МНЕ";

const fallbackParagraphs = [
  "ML/LLM инженер с продуктовым подходом и бэкенд-фоном (Python\u00a0+\u00a0.NET).",
  "Делаю AI-функциональность удобной и надёжной: продумываю архитектуру, забочусь о качестве моделей и интегрирую ML-решения так, чтобы они помогали бизнесу."
];

const fallbackBulletSections: AboutSection[] = [
  {
    title: "LLM / AI-агенты / RAG",
    is_primary: true,
    badge: "focus",
    items: [
      "Fine-tuning моделей и LoRA-адаптеры, векторные пайплайны",
      "Агентные сценарии с инструментальными вызовами (ReAct, LangChain/LangGraph)",
      "RAG-архитектуры: поиск, ранжирование, хранение векторов (ChromaDB, TEI)",
      "Контроль качества ответов, настройка промптов под прод"
    ]
  },
  {
    title: "CV",
    is_primary: false,
    badge: "stack",
    items: [
      "Детекция и сегментация (YOLO, Detectron2)",
      "Пайплайны обработки изображений (подготовка датасетов, аугментации)",
      "Цикл улучшения моделей по ошибкам (валидация, сбор сложных кейсов, дообучение)",
      "Запуск CV-сервисов в прод"
    ]
  },
  {
    title: "Backend / MLOps",
    is_primary: false,
    badge: "stack",
    items: [
      "Backend: Python (FastAPI), C# /.NET (ASP.NET Core), PostgreSQL",
      "Асинхронные задачи: Celery, RabbitMQ, Redis",
      "MLOps: MLflow, пайплайны обучения/дообучения, контейнеризация (Docker)",
      "Интеграции с внешними API и микросервисами"
    ]
  }
];

const summarySplitRegex = /(?<=\.) (?=(?!NET\b)[A-ZА-ЯЁ])/u;

export default function AboutMeSection({ profile, stats, focusAreas = [] }: AboutMeSectionProps) {
  const normalizeSummaryText = (text: string | null) =>
    text ? text.replace(/Python\s*\+\s*\.NET/gi, "Python\u00a0+\u00a0.NET").trim() : null;

  const sections: AboutSection[] =
    focusAreas.length > 0
      ? focusAreas.map((fa) => ({
          title: fa.title,
          is_primary: fa.is_primary,
          badge: fa.is_primary ? "focus" : "stack",
          items: fa.bullets.map((b) => b.text)
        }))
      : fallbackBulletSections;

  const summaryText = normalizeSummaryText((profile as any).summary_md || null);
  const summaryParagraphs =
    summaryText && summaryText.length > 0
      ? summaryText
          .split(/\n+/)
          .flatMap((block) =>
            block
              .split(summarySplitRegex)
              .map((p) => p.trim())
              .filter(Boolean)
          )
      : fallbackParagraphs;

  return (
    <Section id="about" label={sectionLabel} title={sectionTitle} className="mt-28 md:mt-20">
      <div className="grid gap-8 rounded-3xl border border-[#00ffc3]/20 bg-black/40 p-6 shadow-[0_0_15px_rgba(0,255,200,0.16)] backdrop-blur sm:p-8">
        <div className="space-y-4">
          {summaryParagraphs.map((paragraph, idx) => (
            <p
              key={idx}
              className="max-w-3xl text-left text-lg leading-relaxed text-slate-100 md:max-w-4xl"
            >
              {paragraph}
            </p>
          ))}
          <div className="grid gap-6 md:grid-cols-3">
            {sections.map((section) => (
              <div
                key={section.title}
                className="group flex h-full flex-col rounded-3xl border border-[#00ffc3]/20 bg-gradient-to-br from-black/60 via-bg-panel/70 to-black/50 p-6 shadow-[0_0_15px_rgba(0,255,200,0.14)] transition duration-300 hover:border-[#00ffc3]/60 hover:shadow-[0_0_45px_rgba(0,255,200,0.35)]"
              >
                <div className="flex items-center justify-between">
                  <h3 className="font-semibold text-accent-soft">{section.title}</h3>
                  <span className="rounded-full border border-[#00ffc3]/30 px-3 py-1 text-xs uppercase text-accent-soft/80">
                    {(section.badge || (section.is_primary ? "focus" : "stack")).toUpperCase()}
                  </span>
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
