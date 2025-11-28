import AgentMessageList from "@/components/agent/AgentMessageList";
import AgentInput from "@/components/agent/AgentInput";
import { AgentMessage } from "@/lib/types";

type AgentChatWindowProps = {
  messages: AgentMessage[];
  value: string;
  onValueChange: (v: string) => void;
  onSubmit: () => void;
  loading: boolean;
};

export default function AgentChatWindow({
  messages,
  value,
  onValueChange,
  onSubmit,
  loading
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
        disabled={loading}
        suggestions={["Проекты ML", "Где применялся RAG?", "Технологии Python", "Как устроен агент?"]}
      />
      {loading ? <p className="text-right text-[11px] text-accent-soft">Думаю…</p> : null}
    </div>
  );
}
