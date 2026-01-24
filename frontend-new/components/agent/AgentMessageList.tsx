import { useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import clsx from "clsx";

import { AgentMessage } from "@/lib/types";

type AgentMessageListProps = {
  messages: AgentMessage[];
  typing?: boolean;
  canRetry?: boolean;
  onRetry?: (question: string) => void;
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

export default function AgentMessageList({
  messages,
  typing = false,
  canRetry = false,
  onRetry
}: AgentMessageListProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, typing]);

  // Найти последнее сообщение пользователя без ответа
  const findUnansweredUserMessage = (): string | null => {
    if (messages.length === 0) return null;
    const lastMsg = messages[messages.length - 1];
    // Если последнее сообщение - от пользователя, значит нет ответа
    if (lastMsg.role === "user") {
      return lastMsg.id;
    }
    // Если последнее сообщение агента пустое или с ошибкой
    if (lastMsg.role === "agent" && (!lastMsg.content || lastMsg.status === "error")) {
      // Ищем предыдущее сообщение пользователя
      for (let i = messages.length - 2; i >= 0; i--) {
        if (messages[i].role === "user") {
          return messages[i].id;
        }
      }
    }
    return null;
  };

  const unansweredId = findUnansweredUserMessage();

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
          const showRetry = canRetry && onRetry && m.id === unansweredId && m.role === "user";

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
              <div className="flex items-start justify-between gap-2">
                <p className="font-mono text-[10px] uppercase tracking-wider text-accent-soft/80">
                  {m.role === "user" ? "вы" : "агент"}
                </p>
                {showRetry && (
                  <button
                    onClick={() => onRetry(m.content)}
                    className="flex-shrink-0 p-1 rounded hover:bg-accent/20 transition-colors text-accent-soft hover:text-accent"
                    title="Повторить запрос"
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2.5}
                        d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                      />
                    </svg>
                  </button>
                )}
              </div>
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
