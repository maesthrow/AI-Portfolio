import { FormEvent } from "react";

type AgentInputProps = {
  value: string;
  onChange: (v: string) => void;
  onSubmit: () => void;
  disabled?: boolean;
  inputDisabled?: boolean;
  sendDisabled?: boolean;
  suggestions?: string[];
  suggestionsDisabled?: boolean;
  streaming?: boolean;
  onStop?: () => void;
};

const MAX_INPUT_TOKENS = Number(process.env.NEXT_PUBLIC_MAX_INPUT_TOKENS) || 100;
const CHARS_PER_TOKEN = Number(process.env.NEXT_PUBLIC_CHARS_PER_TOKEN) || 4;

export default function AgentInput({
  value,
  onChange,
  onSubmit,
  disabled,
  inputDisabled = false,
  sendDisabled = false,
  suggestions = [],
  suggestionsDisabled = false,
  streaming = false,
  onStop
}: AgentInputProps) {
  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (streaming) return;
    onSubmit();
  };

  const approxTokens = Math.ceil(value.length / CHARS_PER_TOKEN);
  const ratio = approxTokens / MAX_INPUT_TOKENS;
  const showCounter = ratio >= 0.9;
  const isExceeded = approxTokens > MAX_INPUT_TOKENS;

  // Cyberpunk glow colors
  const getCounterColor = () => {
    if (!showCounter) return "";
    if (isExceeded) {
      return "text-red-400 shadow-[0_0_12px_rgba(248,113,113,0.4)] animate-pulse-slow";
    }
    if (approxTokens === MAX_INPUT_TOKENS) {
      return "text-orange-400 shadow-[0_0_10px_rgba(251,146,60,0.4)]";
    }
    return "text-yellow-400 shadow-[0_0_8px_rgba(250,204,21,0.3)]";
  };

  const inputIsDisabled = inputDisabled || disabled;
  const sendIsDisabled = sendDisabled || disabled || streaming || isExceeded;

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2">
        {suggestions.map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => !suggestionsDisabled && onChange(s)}
            disabled={suggestionsDisabled}
            className={`rounded-full border border-accent/40 bg-accent/10 px-3 py-1 text-xs text-slate-100 transition ${
              suggestionsDisabled
                ? 'opacity-50 cursor-not-allowed'
                : 'hover:-translate-y-0.5 hover:shadow-neon'
            }`}
          >
            {s}
          </button>
        ))}
      </div>
      <form onSubmit={handleSubmit} className="flex items-center gap-2">
        <input
          value={value}
          onChange={(e) => onChange(e.target.value)}
          disabled={inputIsDisabled}
          placeholder={inputIsDisabled ? "Ожидание ответа..." : "Напишите вопрос..."}
          className="flex-1 rounded-xl border border-slate-700 bg-black/60 px-3 py-2 text-sm text-slate-100 outline-none ring-accent/30 transition focus:border-accent focus:ring-2 disabled:opacity-50"
          aria-label="Введите вопрос о портфолио"
          aria-describedby={showCounter ? "token-counter" : undefined}
        />
        {streaming ? (
          <button
            type="button"
            onClick={onStop}
            disabled={!onStop}
            className="rounded-xl border border-accent/60 bg-red-500/40 px-3 py-2 text-sm font-semibold text-slate-100 shadow-neon transition hover:-translate-y-0.5 hover:shadow-neon-strong disabled:opacity-50"
          >
            Стоп
          </button>
        ) : (
          <button
            type="submit"
            disabled={sendIsDisabled || !value.trim()}
            className={`rounded-xl border border-accent/60 bg-accent/20 px-3 py-2 text-sm font-semibold shadow-neon transition enabled:hover:-translate-y-0.5 enabled:hover:shadow-neon-strong disabled:opacity-50 ${
              value.trim() ? "text-slate-100" : "text-slate-900"
            }`}
          >
            Отправить
          </button>
        )}
      </form>

      {showCounter && (
        <div className="flex justify-end mt-1">
          <span
            id="token-counter"
            className={`text-xs font-mono transition-all duration-200 ${getCounterColor()}`}
            role="status"
            aria-live="polite"
          >
            {approxTokens} / {MAX_INPUT_TOKENS} токенов
            {isExceeded
              ? " • Слишком длинное сообщение"
              : approxTokens === MAX_INPUT_TOKENS
                ? " • Лимит ввода достигнут"
                : " • Лимит ввода"}
          </span>
        </div>
      )}
    </div>
  );
}
