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
      title="ОБО МНЕ"
      subtitle="ML/LLM инженер и Python-backend разработчик. Запускаю CV и RAG сервисы, довожу их до продакшена."
    >
      <div className="grid gap-6 rounded-3xl border border-slate-700/60 bg-black/30 p-6 backdrop-blur">
        <div className="space-y-4">
          <p className="text-base text-slate-200">
            {profile.subtitle ||
              "Совмещаю опыт создания CV/LLM-продуктов и построения backend-сервисов. Проектирую ML/LLM пайплайны, интеграции, метрики и наблюдаемость. Делаю решения, которые живут в продакшене, а не остаются демо."}
          </p>
          <p className="text-sm text-slate-400">
            Работаю с RAG/агентами, детекцией объектов (YOLO), MLOps, API-интеграциями и .NET сервисами.
          </p>
        </div>
        <StatsGrid stats={stats} />
      </div>
    </Section>
  );
}
