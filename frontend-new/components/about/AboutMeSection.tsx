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
      title="Обо мне"
      subtitle="ML/LLM инженер с бэкграундом Python/.NET backend. Фокус на CV и RAG-системах и поставке надёжных AI-функций end-to-end."
    >
      <div className="grid gap-8 rounded-3xl border border-[#00ffc3]/20 bg-black/40 p-8 shadow-[0_0_25px_rgba(0,255,200,0.25)] backdrop-blur">
        <div className="space-y-4">
          <p className="text-lg leading-relaxed text-gray-300">
            {profile.subtitle ||
              "Делаю CV/LLM-решения на прочной бэкенд-основе. Опыт продакшн-доставки ML/LLM: от прототипов и оценки до деплоя и мониторинга. Комфортно работаю на всём стеке, чтобы быстро выпускать и улучшать без потери надёжности."}
          </p>
          <p className="text-lg leading-relaxed text-gray-300">
            Сильные стороны: RAG и CV-пайплайны, детекция (YOLO), MLOps, проектирование API и интеграции .NET-бэкендов с ML-сервисами.
          </p>
        </div>
        <StatsGrid stats={stats} />
      </div>
    </Section>
  );
}
