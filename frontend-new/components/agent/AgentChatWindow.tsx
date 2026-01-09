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
  streamingStarted?: boolean;
  onStop?: () => void;
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
  onStop
}: AgentChatWindowProps) {
  const typing = loading && !streamingStarted;

  return (
    <div className="flex h-full flex-col gap-3 rounded-2xl border border-accent/40 bg-slate-950/90 p-4 shadow-neon-strong backdrop-blur">
      <div className="flex items-center justify-between">
        <div>
          <p className="font-mono text-xs uppercase text-accent-soft">AI-агент</p>
          <p className="mt-1 text-xs text-slate-300">GigaChat + RAG по данным портфолио</p>
        </div>
        <div className="flex items-center gap-2 rounded-full border border-accent/30 bg-black/50 px-3 py-1 text-[11px] font-semibold text-accent">
          ● online
        </div>
      </div>
      <AgentMessageList messages={messages} typing={typing} />
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
    </div>
  );
}
