import { FormEvent } from "react";

type AgentInputProps = {
  value: string;
  onChange: (v: string) => void;
  onSubmit: () => void;
  disabled?: boolean;
  suggestions?: string[];
};

export default function AgentInput({
  value,
  onChange,
  onSubmit,
  disabled,
  suggestions = []
}: AgentInputProps) {
  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    onSubmit();
  };

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2">
        {suggestions.map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => onChange(s)}
            className="rounded-full border border-accent/40 bg-accent/10 px-3 py-1 text-xs text-slate-100 transition hover:-translate-y-0.5 hover:shadow-neon"
          >
            {s}
          </button>
        ))}
      </div>
      <form onSubmit={handleSubmit} className="flex items-center gap-2">
        <input
          value={value}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          placeholder="Спросите про проекты или опыт..."
          className="flex-1 rounded-xl border border-slate-700 bg-black/60 px-3 py-2 text-sm text-slate-100 outline-none ring-accent/30 transition focus:border-accent focus:ring-2 disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={disabled}
          className="rounded-xl border border-accent/60 bg-accent/20 px-3 py-2 text-sm font-semibold text-slate-900 shadow-neon transition enabled:hover:-translate-y-0.5 enabled:hover:shadow-neon-strong disabled:opacity-50"
        >
          Отправить
        </button>
      </form>
    </div>
  );
}
