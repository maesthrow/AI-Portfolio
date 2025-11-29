import Section from "@/components/layout/Section";
import StatsGrid from "@/components/about/StatsGrid";
import { Profile, StatItem } from "@/lib/types";

type AboutMeSectionProps = {
  profile: Profile;
  stats: StatItem[];
};

export default function AboutMeSection({ profile, stats }: AboutMeSectionProps) {
  return (
    <Section
      id="about"
      label="ОБО МНЕ"
      title="Обо мне"
      subtitle="ML/LLM инженер и продуктовый разработчик на стыке Python/.NET backend и CV/RAG-решений."
    >
      <div className="grid gap-8 rounded-3xl border border-[#00ffc3]/20 bg-black/40 p-6 shadow-[0_0_25px_rgba(0,255,200,0.25)] backdrop-blur sm:p-8">
        <div className="space-y-4">
          <p className="max-w-3xl text-left text-lg leading-relaxed text-gray-300 md:max-w-4xl">
            {profile.subtitle ||
              "Делаю CV/LLM-решения на продуктовый цикл. Веду стратегию-реализацию ML/LLM: от исследовательских POC и оценки данных до запуска и поддержки. Работаю с командами и бизнесом, чтобы фичи давали эффект."}
          </p>
          <p className="max-w-3xl text-left text-lg leading-relaxed text-gray-300 md:max-w-4xl">
            Основной стек: RAG и CV-пайплайны, детекция (YOLO), MLOps, интеграции API и сопряжение
            .NET-сервисов с ML-компонентами.
          </p>
        </div>
        <StatsGrid stats={stats} />
      </div>
    </Section>
  );
}
