"use client";
import { useEffect, useRef, useState } from "react";

type Msg = {
  role: "user" | "agent";
  text: string;
  sources?: any[];
  typing?: boolean;
  tempId?: string;
};

export type ChatDockProps = {
  collection?: string;
  systemPrompt?: string;
  width?: number;
  height?: number;
};

export default function ChatDock({
  collection,
  systemPrompt,
  width,
  height,
}: ChatDockProps) {
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const [messages, setMessages] = useState<Msg[]>([]);
  const [showIntro, setShowIntro] = useState(true); // стартовые подсказки

  const listRef = useRef<HTMLDivElement | null>(null);
  const typingTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const boxWidth = width ?? 360;
  const boxHeight = height ?? 420;
  const BAR_H = 46;

  // автопрокрутка вниз
  const scrollToBottom = (smooth = true) => {
    const el = listRef.current;
    if (!el) return;
    requestAnimationFrame(() => {
      el.scrollTo({ top: el.scrollHeight, behavior: smooth ? "smooth" : "auto" });
    });
  };

  useEffect(() => {
    scrollToBottom(false);
  }, []);

  useEffect(() => {
    const el = listRef.current;
    if (!el || messages.length === 0) return;
    const last = messages[messages.length - 1];
    const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 120;
    if (last.role === "agent" || nearBottom) scrollToBottom(true);
  }, [messages]);

  // «Думаю…»
  const startTypingBubble = () => {
    const tempId = `typing_${Date.now()}`;
    setMessages((m) => [...m, { role: "agent", text: "Думаю", typing: true, tempId }]);
    let dots = 0;
    typingTimerRef.current = setInterval(() => {
      dots = (dots + 1) % 4;
      setMessages((m) =>
        m.map((msg) =>
          msg.typing && msg.tempId === tempId
            ? { ...msg, text: "Думаю" + (dots ? " " + ".".repeat(dots) : "") }
            : msg
        )
      );
    }, 350);
    return tempId;
  };

  const stopTypingBubbleAndReplace = (tempId: string, final: Omit<Msg, "typing" | "tempId">) => {
    if (typingTimerRef.current) {
      clearInterval(typingTimerRef.current);
      typingTimerRef.current = null;
    }
    setMessages((m) => m.map((msg) => (msg.typing && msg.tempId === tempId ? { ...final } : msg)));
  };

  function ask(q: string) {
    setInput(q);
    setTimeout(() => handleSend(), 0);
  }

  async function handleSend() {
    const userText = input.trim();
    if (!userText || busy) return;

    // скрываем интро при первом сообщении
    if (showIntro) setShowIntro(false);

    setMessages((m) => [...m, { role: "user", text: userText }]);
    setInput("");
    setBusy(true);

    const RAG = process.env.NEXT_PUBLIC_RAG_API_URL || "http://localhost:8004";
    const payload: Record<string, any> = { question: userText, k: 10 };
    if (collection) payload.collection = collection;
    if (systemPrompt) payload.system_prompt = systemPrompt.trim();

    const typingId = startTypingBubble();

    try {
      const resp = await fetch(`${RAG}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!resp.ok) {
        const text = await resp.text();
        throw new Error(text || `HTTP ${resp.status}`);
      }
      const data = await resp.json();
      stopTypingBubbleAndReplace(typingId, {
        role: "agent",
        text: data.answer || "(нет ответа)",
        sources: data.sources || [],
      });
    } catch (e: any) {
      stopTypingBubbleAndReplace(typingId, {
        role: "agent",
        text: `Ошибка запроса: ${e?.message || e}`,
      });
    } finally {
      setBusy(false);
    }
  }

  const containerHeight = collapsed
    ? BAR_H
    : Math.min(boxHeight, Math.round(typeof window !== "undefined" ? window.innerHeight * 0.8 : boxHeight));
  const containerWidth = Math.min(
    boxWidth,
    Math.round(typeof window !== "undefined" ? window.innerWidth * 0.92 : boxWidth)
  );

  const canSend = !busy && input.trim().length > 0;

  return (
    <div
      style={{
        position: "fixed",
        right: 16,
        bottom: 16,
        width: containerWidth,
        height: containerHeight,
        background: "#0f131a",
        border: "1px solid #1f2430",
        borderRadius: 12,
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
        zIndex: 50,
        transition: "height .18s ease",
      }}
    >
      {/* header */}
      <div
        style={{
          padding: "8px 10px",
          borderBottom: collapsed ? "none" : "1px solid #1f2430",
          fontSize: 12,
          color: "#9aa4b2",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 8,
        }}
      >
        <div style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          <b style={{ color: "#cdd6f4" }}>AI-Portfolio Agent</b>
          {collection ? ` · RAG: ${collection}` : " · Qwen2.5"}
        </div>

        <button
          onClick={() => setCollapsed((v) => !v)}
          aria-label={collapsed ? "Развернуть чат" : "Свернуть чат"}
          title={collapsed ? "Развернуть чат" : "Свернуть чат"}
          style={{
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            width: 28,
            height: 28,
            borderRadius: 8,
            border: "1px solid #273043",
            background: "#0b0f15",
            color: "#cdd6f4",
            cursor: "pointer",
          }}
        >
          {collapsed ? "✨" : "➖"}
        </button>
      </div>

      {/* список сообщений + стартовый экран */}
      {!collapsed && (
        <>
          <div
            ref={listRef}
            aria-live="polite"
            style={{
              position: "relative",
              flex: 1,
              overflowY: "auto",
              padding: 10,
              display: "grid",
              gap: 8,
            }}
          >
            {/* Intro overlay */}
            {showIntro && messages.length === 0 && (
              <div
                style={{
                  position: "absolute",
                  inset: 0,
                  display: "grid",
                  placeItems: "center",
                  padding: 20,
                  textAlign: "center",
                }}
              >
                <div
                  style={{
                    maxWidth: 360,
                    color: "#cdd6f4",
                    fontSize: 13,
                    lineHeight: 1.6,
                    opacity: 0.95,
                    display: "grid",
                    justifyItems: "center",
                    gap: 14,                 // ↑ общий вертикальный ритм
                  }}
                >
                  {/* friendly intro */}
                  <div style={{ fontWeight: 600, fontSize: 14 }}>
                    Готов помочь с вопросами о моем опыте
                  </div>

                  <div className="hint" style={{ marginTop: 2, marginBottom: -2 }}>
                    Спросите, например:
                  </div>

                  {/* блок с примерами — отдельный отступ и больший gap */}
                  <div
                    style={{
                      display: "grid",
                      gap: 10,               // ↑ расстояние между чипами
                      justifyItems: "center",
                      marginTop: 4,          // ↑ дыхание между подзаголовком и чипами
                      width: "100%",
                    }}
                  >
                    {[
                      "Где применялся RAG?",
                      "Какие базы данных использовал?",
                      "Чем занимался в компании Aston?",
                    ].map((q) => (
                      <button
                        key={q}
                        onClick={() => ask(q)}
                        style={{
                          padding: "8px 14px",               // ↑ выше и шире
                          borderRadius: 999,
                          border: "1px solid #243046",
                          background: "#0b0f15",
                          color: "#cdd6f4",
                          fontSize: 12,
                          lineHeight: 1.4,
                          cursor: "pointer",
                          opacity: 0.92,
                          boxShadow: "0 0 0 1px rgba(255,255,255,0.02) inset",
                          transition: "background .15s ease, opacity .15s ease",
                        }}
                      >
                        {q}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {messages.map((m, i) => (
              <div key={m.tempId ?? i}>
                <div
                  style={{
                    fontSize: 12,
                    color: m.role === "user" ? "#e6edf3" : "#cdd6f4",
                    opacity: m.typing ? 0.85 : 1,
                    fontStyle: m.typing ? "italic" : "normal",
                  }}
                >
                  <b>{m.role === "user" ? "Вы" : "Агент"}</b>: {m.text}
                </div>

                {/* Источники — без score */}
                {!m.typing && m.sources?.length ? (
                  <div style={{ marginTop: 4 }}>
                    <div className="hint">Источники:</div>
                    <ul style={{ margin: 0, paddingLeft: 18 }}>
                      {m.sources.map((s: any, j: number) => (
                        <li key={j} className="hint mono">
                          {s.title || s.id || "(источник)"}
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}
              </div>
            ))}
          </div>

            {/* input + send button */}
            <div style={{ padding: 10, borderTop: "1px solid #1f2430" }}>
              <div style={{ position: "relative" }}>
                <input
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSend()}
                  placeholder={busy ? "Ожидание ответа..." : "Напишите вопрос…"}
                  disabled={busy}
                  style={{
                    width: "100%",
                    background: "#0b0f15",
                    color: "#e6edf3",
                    border: "1px solid #273043",
                    borderRadius: 8,
                    padding: "8px 38px 8px 10px", // место под кнопку справа
                    outline: "none",
                    opacity: busy ? 0.8 : 1,
                  }}
                />

                <button
                  onClick={handleSend}
                  disabled={!canSend}
                  aria-label="Отправить сообщение"
                  title={canSend ? "Отправить" : "Напишите сообщение"}
                  style={{
                    position: "absolute",
                    right: 4,
                    top: "50%",
                    transform: "translateY(-50%)",
                    width: 32,
                    height: 32,
                    // «невидимая» зона клика:
                    background: "transparent",
                    border: "none",
                    padding: 0,
                    cursor: canSend ? "pointer" : "default",
                    display: "inline-flex",
                    alignItems: "center",
                    justifyContent: "center",
                    // плавные эффекты:
                    transition: "filter .15s ease, opacity .15s ease",
                    opacity: canSend ? 0.95 : 0.5,
                    // кастомный focus-«ринговый» контур:
                    outline: "none",
                    boxShadow: "none",
                  }}
                  onMouseEnter={(e) => {
                    if (canSend) (e.currentTarget.style.filter = "drop-shadow(0 0 6px rgba(205,214,244,.25))");
                  }}
                  onMouseLeave={(e) => {
                    (e.currentTarget.style.filter = "none");
                  }}
                >
                  <svg
                      width="16" height="16" viewBox="0 0 24 24" fill="none"
                      stroke={canSend ? "#cdd6f4" : "#8a94a3"} strokeWidth="2"
                      strokeLinecap="round" strokeLinejoin="round"
                      style={{
                        transform: "rotate(8deg)",      // ← угол наклона носика
                        transformOrigin: "50% 50%",
                        transition: "transform .15s ease"
                      }}
                    >
                      <path d="M22 2L11 13"></path>
                      <path d="M22 2l-7 20-4-9-9-4 20-7z"></path>
                    </svg>
                </button>
              </div>
            </div>
        </>
      )}
    </div>
  );
}
