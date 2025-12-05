import { useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import clsx from "clsx";

import { AgentMessage } from "@/lib/types";

type AgentMessageListProps = {
  messages: AgentMessage[];
  typing?: boolean;
};

const TypingDots = () => (
  <div className="flex items-center gap-1 pt-1">
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

export default function AgentMessageList({ messages, typing = false }: AgentMessageListProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, typing]);

  return (
    <div
      ref={scrollRef}
      className="flex flex-1 flex-col gap-3 overflow-y-auto rounded-xl bg-black/40 p-3 text-sm"
    >
      {messages.length === 0 ? (
        <div className="flex flex-1 items-center justify-center text-center text-sm text-slate-400">
          Спросите агента о моих проектах, опыте или технологиях.
        </div>
      ) : (
        messages.map((m, idx) => {
          const isLast = idx === messages.length - 1;
          const showTyping = typing && m.role === "agent" && m.status === "streaming" && isLast;

          return (
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
                {m.role === "user" ? "вы" : "агент"}
              </p>
              <div className="mt-1 text-sm leading-relaxed">
                {showTyping ? (
                  <TypingDots />
                ) : (
                  <ReactMarkdown
                    components={{
                      p: ({ node, ...props }) => (
                        <p className="whitespace-pre-wrap leading-relaxed" {...props} />
                      ),
                      strong: ({ node, ...props }) => <strong className="font-semibold" {...props} />,
                      ul: ({ node, ...props }) => <ul className="ml-4 list-disc space-y-1" {...props} />,
                      ol: ({ node, ...props }) => <ol className="ml-4 list-decimal space-y-1" {...props} />,
                      li: ({ node, ...props }) => <li className="whitespace-pre-wrap" {...props} />,
                      code: ({ node, className, ...props }) => {
                        const isInline = !className?.includes("language-");
                        return isInline ? (
                          <code className="rounded bg-slate-800 px-1 py-0.5 text-xs" {...props} />
                        ) : (
                          <code
                            className="block whitespace-pre-wrap rounded bg-slate-900 px-3 py-2 text-xs"
                            {...props}
                          />
                        );
                      }
                    }}
                  >
                    {m.content}
                  </ReactMarkdown>
                )}
              </div>
            </div>
          );
        })
      )}
    </div>
  );
}
