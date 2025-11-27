"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { askAgent } from "@/lib/api";
import AgentChatWindow from "@/components/agent/AgentChatWindow";
import { AgentMessage } from "@/lib/types";
import clsx from "clsx";

const generateSessionId = () => {
  const cryptoObj = typeof globalThis !== "undefined" ? (globalThis as any).crypto : undefined;
  if (cryptoObj && typeof cryptoObj.randomUUID === "function") {
    return cryptoObj.randomUUID();
  }
  if (cryptoObj && typeof cryptoObj.getRandomValues === "function") {
    const arr = new Uint32Array(4);
    cryptoObj.getRandomValues(arr);
    return Array.from(arr, (n) => n.toString(16).padStart(8, "0")).join("-");
  }
  return `sess-${Date.now()}-${Math.random().toString(16).slice(2)}`;
};

export default function AgentDock() {
  const [isOpen, setIsOpen] = useState(false);
  const [hintShown, setHintShown] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [messages, setMessages] = useState<AgentMessage[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [loading, setLoading] = useState(false);
  const sessionIdRef = useRef<string>();

  if (!sessionIdRef.current) {
    sessionIdRef.current = generateSessionId();
  }

  useEffect(() => {
    const onResize = () => setIsMobile(window.innerWidth < 768);
    onResize();
    window.addEventListener("resize", onResize);
    const t = setTimeout(() => setHintShown(true), 2500);
    return () => {
      window.removeEventListener("resize", onResize);
      clearTimeout(t);
    };
  }, []);

  const sessionId = sessionIdRef.current;

  const handleSend = async () => {
    if (!inputValue.trim() || loading) return;
    const content = inputValue.trim();
    const userMessage: AgentMessage = {
      id: `${Date.now()}-u`,
      role: "user",
      content,
      createdAt: Date.now()
    };
    setMessages((prev) => [...prev, userMessage]);
    setInputValue("");
    setLoading(true);
    try {
      const result = await askAgent(content, sessionId);
      const agentMessage: AgentMessage = {
        id: `${Date.now()}-a`,
        role: "agent",
        content: result.answer || "Готово.",
        createdAt: Date.now()
      };
      setMessages((prev) => [...prev, agentMessage]);
    } catch (e) {
      const errorMessage: AgentMessage = {
        id: `${Date.now()}-err`,
        role: "agent",
        content: "Не получилось связаться с агентом. Попробуйте позже.",
        createdAt: Date.now()
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const buttonLabel = "AI-агент";
  //const buttonLabel = useMemo(() => (isMobile ? "AI" : "AI-агент"), [isMobile]);

  return (
    <div className="pointer-events-none fixed bottom-4 right-4 z-50 flex flex-col items-end gap-3">
      <button
        onClick={() => setIsOpen((v) => !v)}
        className="pointer-events-auto flex items-center gap-3 rounded-full border border-accent/40 bg-gradient-to-r from-accent/20 via-accent-soft/20 to-accent/10 px-4 py-2 text-sm font-semibold text-slate-100 shadow-neon transition-all duration-200 hover:-translate-y-0.5 hover:shadow-neon-strong"
      >
        <span className="relative flex h-2 w-2">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-accent opacity-75" />
          <span className="relative inline-flex h-2 w-2 rounded-full bg-accent-soft" />
        </span>
        {buttonLabel}
      </button>

      {isOpen ? (
        <div
          className={clsx(
            "pointer-events-auto overflow-hidden rounded-3xl border border-accent/50 shadow-neon-strong backdrop-blur",
            isMobile ? "w-[92vw] max-w-md" : "w-[380px]"
          )}
          style={{ height: isMobile ? "70vh" : "520px" }}
        >
          <AgentChatWindow
            messages={messages}
            value={inputValue}
            onValueChange={setInputValue}
            onSubmit={handleSend}
            loading={loading}
          />
        </div>
      ) : null}

      {!isOpen && isMobile && hintShown ? (
        <div className="pointer-events-none mb-1 rounded-xl border border-accent/40 bg-black/70 px-3 py-2 text-xs text-slate-100 shadow-neon">
          Спроси агента обо мне и моих проектах →
        </div>
      ) : null}
    </div>
  );
}
