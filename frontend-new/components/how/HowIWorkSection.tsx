import Section from "@/components/layout/Section";

type PillItem = {
  title: string;
  bullets: string[];
};

const items: PillItem[] = [
  {
    title: "Вижу, куда движется AI",
    bullets: [
      "Выделяю реальные use-cases в CV, LLM/RAG, ML-сервисах",
      "Собираю MVP быстро, отбираю метрики и проверяю гипотезы",
      "Отсекаю “AI ради хайпа”, фокус на бизнес-ценности"
    ]
  },
  {
    title: "Проектирую архитектуры",
    bullets: [
      "Датасеты, обучение, инференс, API — единый пайплайн",
      "RAG/агенты: retrieval, ранжирование, оценка качества",
      "Интеграция с существующими сервисами, контроль версий"
    ]
  },
  {
    title: "Довожу до продакшена",
    bullets: [
      "CI/CD, мониторинг качества и латентности",
      "Обслуживание моделей: тюнинг, обновления, rollback",
      "Работаю с командами: dev, data, продукт"
    ]
  }
];

export default function HowIWorkSection() {
  return (
    <Section
      id="how-i-work"
      title="КАК Я РАБОТАЮ С AI"
      subtitle="От видения продукта до продакшена: RAG/агенты, CV, ML-сервисы, интеграции."
    >
      <div className="grid gap-4 lg:grid-cols-3">
        {items.map((item) => (
          <div
            key={item.title}
            className="group rounded-2xl border border-accent/30 bg-gradient-to-br from-accent/5 via-bg-panel to-black/40 p-5 shadow-neon transition-transform duration-200 hover:-translate-y-1 hover:shadow-neon-strong"
          >
            <p className="font-mono text-sm text-accent-soft"># {item.title}</p>
            <ul className="mt-3 space-y-2 text-sm text-slate-200">
              {item.bullets.map((b) => (
                <li key={b} className="flex items-start gap-2">
                  <span className="mt-1 h-1.5 w-1.5 rounded-full bg-accent-soft" />
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
