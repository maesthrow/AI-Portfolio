"use client";

import { useEffect, useRef, useState } from "react";
import clsx from "clsx";

import AgentChatWindow from "@/components/agent/AgentChatWindow";
import { askAgent, callAgentStream, ChatStreamEvent } from "@/lib/api";
import { AgentMessage } from "@/lib/types";

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
  const sessionIdRef = useRef<string>(generateSessionId());
  const streamControllerRef = useRef<AbortController | null>(null);
  const charQueueRef = useRef<string[]>([]);
  const frameRef = useRef<number | null>(null);
  const activeAgentIdRef = useRef<string | null>(null);

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

  const updateAgentMessage = (tempId: string, updater: (m: AgentMessage) => AgentMessage) => {
    setMessages((prev) =>
      prev.map((m) => (m.tempId === tempId || m.id === tempId ? updater(m) : m))
    );
  };

  const stopCharPump = () => {
    if (frameRef.current) {
      cancelAnimationFrame(frameRef.current);
      frameRef.current = null;
    }
  };

  const pumpChars = (targetId: string) => {
    if (!charQueueRef.current.length) {
      frameRef.current = null;
      return;
    }
    const nextChar = charQueueRef.current.shift() as string;
    updateAgentMessage(targetId, (m) => ({ ...m, content: (m.content || "") + nextChar }));
    frameRef.current = requestAnimationFrame(() => pumpChars(targetId));
  };

  const enqueueChars = (targetId: string, text: string) => {
    if (!text) return;
    charQueueRef.current.push(...text);
    if (!frameRef.current) {
      pumpChars(targetId);
    }
  };

  const handleSend = async () => {
    if (!inputValue.trim() || loading) return;
    const question = inputValue.trim();
    const sessionId = sessionIdRef.current;
    const tempId = `${Date.now()}-agent`;

    const userMessage: AgentMessage = {
      id: `${Date.now()}-user`,
      role: "user",
      content: question,
      createdAt: Date.now()
    };
    const agentPlaceholder: AgentMessage = {
      id: tempId,
      tempId,
      role: "agent",
      content: "",
      createdAt: Date.now(),
      status: "streaming"
    };

    setMessages((prev) => [...prev, userMessage, agentPlaceholder]);
    setInputValue("");
    setLoading(true);

    const controller = new AbortController();
    streamControllerRef.current = controller;

    activeAgentIdRef.current = tempId;
    charQueueRef.current = [];
    stopCharPump();

    const applyError = (message: string) => {
      updateAgentMessage(tempId, (m) => ({
        ...m,
        content: message,
        status: "error"
      }));
    };

    try {
      const stream = await callAgentStream(
        { question, session_id: sessionId },
        { signal: controller.signal }
      );

      for await (const event of stream as AsyncIterable<ChatStreamEvent>) {
        if (event.type === "start" && event.message_id) {
          updateAgentMessage(tempId, (m) => ({ ...m, id: event.message_id }));
        } else if (event.type === "delta") {
          enqueueChars(tempId, event.content);
          updateAgentMessage(tempId, (m) => ({
            ...m,
            status: "streaming"
          }));
        } else if (event.type === "error") {
          applyError(`Ошибка агента: ${event.message}`);
        }
      }

      updateAgentMessage(tempId, (m) => ({
        ...m,
        status: m.status === "error" ? m.status : "done"
      }));
    } catch (err: any) {
      if (err?.name === "AbortError") {
        stopCharPump();
        charQueueRef.current = [];
        updateAgentMessage(tempId, (m) => ({
          ...m,
          content: m.content || "Ответ остановлен.",
          status: "stopped"
        }));
      } else {
        console.error("Streaming agent failed, falling back to sync", err);
        try {
          const fallback = await askAgent(question, sessionId);
          stopCharPump();
          charQueueRef.current = [];
          updateAgentMessage(tempId, (m) => ({
            ...m,
            content: fallback.answer,
            status: "done"
          }));
        } catch (fallbackErr) {
          console.error("Fallback agent failed", fallbackErr);
          applyError("Не получилось связаться с агентом. Попробуйте позже.");
        }
      }
    } finally {
      setLoading(false);
      streamControllerRef.current = null;
      activeAgentIdRef.current = null;
      if (!charQueueRef.current.length) {
        stopCharPump();
      }
    }
  };

  const handleStop = () => {
    if (streamControllerRef.current) {
      streamControllerRef.current.abort();
    }
  };

  const buttonLabel = "AI-агент";

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
            onStop={handleStop}
          />
        </div>
      ) : null}

      {!isOpen && isMobile && hintShown ? (
        <div className="pointer-events-none mb-1 rounded-xl border border-accent/40 bg-black/70 px-3 py-2 text-xs text-slate-100 shadow-neon">
          Спросите агента обо мне и моих проектах
        </div>
      ) : null}
    </div>
  );
}
