import { AgentMessage } from "@/lib/types";
import clsx from "clsx";

type AgentMessageListProps = {
  messages: AgentMessage[];
};

export default function AgentMessageList({ messages }: AgentMessageListProps) {
  return (
    <div className="flex flex-1 flex-col gap-3 overflow-y-auto rounded-xl bg-black/40 p-3 text-sm">
      {messages.length === 0 ? (
        <div className="text-center text-xs text-slate-500">
          Спроси агента о проектах, опыте или технологиях.
        </div>
      ) : (
        messages.map((m) => (
          <div
            key={m.id}
            className={clsx(
              "rounded-xl border px-3 py-2",
              m.role === "user"
                ? "border-accent/40 bg-accent/10 text-slate-50"
                : "border-slate-700/70 bg-slate-900/60 text-slate-100"
            )}
          >
            <p className="font-mono text-[10px] uppercase tracking-wider text-accent-soft/80">
              {m.role === "user" ? "you" : "agent"}
            </p>
            <p className="mt-1 whitespace-pre-wrap leading-relaxed">{m.content}</p>
          </div>
        ))
      )}
    </div>
  );
}
