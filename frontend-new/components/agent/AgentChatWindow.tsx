import AgentMessageList from "@/components/agent/AgentMessageList";
import AgentInput from "@/components/agent/AgentInput";
import { AgentMessage } from "@/lib/types";

type AgentChatWindowProps = {
  messages: AgentMessage[];
  value: string;
  onValueChange: (v: string) => void;
  onSubmit: () => void;
  loading: boolean;
  inputDisabled?: boolean;
  sendDisabled?: boolean;
  streaming?: boolean;
  onStop?: () => void;
};

const LoadingDots = () => (
  <div className="flex items-center justify-end gap-1">
    {[0, 1, 2].map((i) => (
      <span
        key={i}
        className="h-2 w-2 rounded-full bg-accent-soft"
        style={{
          animation: "pulse 1s ease-in-out infinite",
          animationDelay: `${i * 0.15}s`
        }}
      />
    ))}
    <style jsx>{`
      @keyframes pulse {
        0% {
          transform: translateY(0);
          opacity: 0.6;
        }
        50% {
          transform: translateY(-4px);
          opacity: 1;
        }
        100% {
          transform: translateY(0);
          opacity: 0.6;
        }
      }
    `}</style>
  </div>
);

export default function AgentChatWindow({
  messages,
  value,
  onValueChange,
  onSubmit,
  loading,
  inputDisabled = false,
  sendDisabled = false,
  streaming = false,
  onStop
}: AgentChatWindowProps) {
  return (
    <div className="flex h-full flex-col gap-3 rounded-2xl border border-accent/40 bg-slate-950/90 p-4 shadow-neon-strong backdrop-blur">
      <div className="flex items-center justify-between">
        <div>
          <p className="font-mono text-xs uppercase text-accent-soft">AI-агент</p>
          <p className="mt-0.5 text-sm text-slate-400">RAG по данным портфолио</p>
        </div>
        <div className="flex items-center gap-2 rounded-full border border-accent/30 bg-black/50 px-3 py-1 text-[11px] font-semibold text-accent">
          ● online
        </div>
      </div>
      <AgentMessageList messages={messages} />
      <AgentInput
        value={value}
        onChange={onValueChange}
        onSubmit={onSubmit}
        disabled={false}
        inputDisabled={inputDisabled}
        sendDisabled={sendDisabled}
        streaming={streaming}
        onStop={onStop}
        suggestions={["Проекты ML", "Где применяется RAG?", "Технологии Python", "Как устроен агент?"]}
      />
      {loading ? <LoadingDots /> : null}
    </div>
  );
}
