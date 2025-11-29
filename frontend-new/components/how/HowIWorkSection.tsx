import Section from "@/components/layout/Section";

type PillItem = {
  title: string;
  bullets: string[];
};

const items: PillItem[] = [
  {
    title: "Product-first поставка AI",
    bullets: [
      "Проясняю use-case'ы для CV, LLM/RAG и ML-пайплайнов с метриками результата.",
      "Быстро прототипирую, проверяю на пользователях и укрепляю под продакшн.",
      "Делаю выбор в AI прагматично: данные, задержка, стоимость и наблюдаемость."
    ]
  },
  {
    title: "Архитектура и системное мышление",
    bullets: [
      "Проектирую чистые API, стриминг и границы сервисов под стабильные релизы.",
      "Фокус в RAG/CV: качество retrieval, оценка, стабильные SLA инференса.",
      "Предпочитаю воспроизводимые пайплайны и мониторинг вместо разовых правок."
    ]
  },
  {
    title: "Запуск и эксплуатация",
    bullets: [
      "CI/CD, feature flags и откаты, чтобы выпускать безопасно и часто.",
      "Паттерны устойчивости: ретраи, backpressure, плавная деградация.",
      "Работаю с dev/data/infra-командами, чтобы среды оставались согласованными."
    ]
  }
];

export default function HowIWorkSection() {
  return (
    <Section
      id="how-i-work"
      title="Как я работаю с AI-продуктами"
      subtitle="Процесс доставки RAG, CV и ML-систем с надёжной интеграцией бэкенда."
    >
      <div className="grid gap-8 lg:grid-cols-3">
        {items.map((item) => (
          <div
            key={item.title}
            className="group rounded-3xl border border-[#00ffc3]/25 bg-gradient-to-br from-accent/10 via-bg-panel to-black/50 p-8 shadow-[0_0_25px_rgba(0,255,200,0.2)] transition-transform duration-300 hover:-translate-y-1 hover:scale-105 hover:border-[#00ffc3]/60 hover:shadow-[0_0_45px_rgba(0,255,200,0.35)]"
          >
            <p className="font-mono text-sm text-accent-soft"># {item.title}</p>
            <ul className="mt-4 space-y-3 text-[1.05rem] leading-relaxed text-gray-300">
              {item.bullets.map((b) => (
                <li key={b} className="flex items-start gap-3">
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
