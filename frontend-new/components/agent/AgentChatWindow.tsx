import AgentMessageList from "@/components/agent/AgentMessageList";
import AgentInput from "@/components/agent/AgentInput";
import { RateLimitWarning } from "@/components/agent/RateLimitWarning";
import { RateLimitBlocked } from "@/components/agent/RateLimitBlocked";
import { AgentMessage, RateLimitInfo, RateLimitError } from "@/lib/types";

type AgentChatWindowProps = {
  messages: AgentMessage[];
  value: string;
  onValueChange: (v: string) => void;
  onSubmit: () => void;
  loading: boolean;
  inputDisabled?: boolean;
  sendDisabled?: boolean;
  streaming?: boolean;
  streamingStarted?: boolean;
  onStop?: () => void;
  rateLimitInfo?: RateLimitInfo | null;
  rateLimitError?: RateLimitError | null;
  onRateLimitRetry?: () => void;
};

export default function AgentChatWindow({
  messages,
  value,
  onValueChange,
  onSubmit,
  loading,
  inputDisabled = false,
  sendDisabled = false,
  streaming = false,
  streamingStarted = false,
  onStop,
  rateLimitInfo,
  rateLimitError,
  onRateLimitRetry
}: AgentChatWindowProps) {
  const typing = loading && !streamingStarted;

  // Определить статус для отображения
  const isBlocked = !!rateLimitError;
  const showWarning = rateLimitInfo?.show_warning && !rateLimitError;

  return (
    <div className="flex h-full flex-col gap-3 rounded-2xl border border-accent/40 bg-slate-950/90 p-4 shadow-neon-strong backdrop-blur">
      <div className="flex items-center justify-between">
        <div>
          <p className="font-mono text-xs uppercase text-accent-soft">AI-агент</p>
          <p className="mt-1 text-xs text-slate-300">GigaChat + RAG по данным портфолио</p>
        </div>
        <div className={`flex items-center gap-2 rounded-full border px-3 py-1 text-[11px] font-semibold ${
          isBlocked
            ? 'border-red-500/30 bg-red-950/50 text-red-400'
            : 'border-accent/30 bg-black/50 text-accent'
        }`}>
          {isBlocked ? '● offline' : '● online'}
        </div>
      </div>
      <AgentMessageList messages={messages} typing={typing} />

      {/* Rate limit warning */}
      {showWarning && rateLimitInfo && (
        <RateLimitWarning info={rateLimitInfo} />
      )}

      {/* Rate limit blocked or normal input */}
      {rateLimitError ? (
        <RateLimitBlocked
          message={rateLimitError.message}
          resetInSeconds={rateLimitError.details?.reset_in_seconds}
          isServiceUnavailable={rateLimitError.code === 'SERVICE_UNAVAILABLE'}
          onRetry={onRateLimitRetry}
        />
      ) : (
        <AgentInput
          value={value}
          onChange={onValueChange}
          onSubmit={onSubmit}
          disabled={false}
          inputDisabled={inputDisabled}
          sendDisabled={sendDisabled}
          streaming={streaming}
          onStop={onStop}
          suggestions={["Расскажи об ML-проектах", "Где применял RAG?", "Опыт с LLM и агентами", "Как можно связаться?"]}
        />
      )}
    </div>
  );
}
