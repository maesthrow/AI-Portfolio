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
  const currentOutputIdRef = useRef<string | null>(null);
  const lastTickRef = useRef<number>(performance.now());
  const releasePendingRef = useRef<boolean>(false);
  const [streamingStarted, setStreamingStarted] = useState(false);

  // Настраиваемая скорость печати
  const CHARS_PER_SECOND = Number(process.env.NEXT_PUBLIC_CHARS_PER_SECOND) || 60;
  const MAX_CHARS_PER_TICK = Number(process.env.NEXT_PUBLIC_MAX_CHARS_PER_TICK) || 4;

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

  const tryReleaseLoading = () => {
    if (releasePendingRef.current && charQueueRef.current.length === 0) {
      setLoading(false);
      releasePendingRef.current = false;
      currentOutputIdRef.current = null;
      setStreamingStarted(false);
    }
  };

  const pumpChars = (targetId: string) => {
    if (!charQueueRef.current.length) {
      frameRef.current = null;
      tryReleaseLoading();
      return;
    }

    const now = performance.now();
    const intervalMs = 1000 / CHARS_PER_SECOND;

    if (now - lastTickRef.current < intervalMs) {
      frameRef.current = requestAnimationFrame(() => pumpChars(targetId));
      return;
    }

    const elapsed = now - lastTickRef.current;
    lastTickRef.current = now;
    const budget = Math.max(1, Math.floor(elapsed / intervalMs));
    const take = Math.min(MAX_CHARS_PER_TICK, budget, charQueueRef.current.length);
    const chunk = charQueueRef.current.splice(0, take).join("");

    if (chunk) {
      updateAgentMessage(targetId, (m) => ({ ...m, content: (m.content || "") + chunk }));
    }

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
    setStreamingStarted(false);
    releasePendingRef.current = false;

    const controller = new AbortController();
    streamControllerRef.current = controller;

    activeAgentIdRef.current = tempId;
    currentOutputIdRef.current = tempId;
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
          currentOutputIdRef.current = event.message_id;
          updateAgentMessage(tempId, (m) => ({ ...m, id: event.message_id }));
        } else if (event.type === "delta") {
          if (!streamingStarted) {
            setStreamingStarted(true);
          }
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
      releasePendingRef.current = true;
      tryReleaseLoading();
    } catch (err: any) {
      if (err?.name === "AbortError") {
        stopCharPump();
        charQueueRef.current = [];
        updateAgentMessage(tempId, (m) => ({
          ...m,
          content: m.content || "Ответ остановлен.",
          status: "stopped"
        }));
        releasePendingRef.current = true;
        tryReleaseLoading();
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
          releasePendingRef.current = true;
          tryReleaseLoading();
        } catch (fallbackErr) {
          console.error("Fallback agent failed", fallbackErr);
          applyError("Не получилось связаться с агентом. Попробуйте позже.");
          releasePendingRef.current = true;
          tryReleaseLoading();
        }
      }
    } finally {
      streamControllerRef.current = null;
      activeAgentIdRef.current = null;
      if (!charQueueRef.current.length) {
        stopCharPump();
        tryReleaseLoading();
      }
    }
  };

  const handleStop = () => {
    const targetId = currentOutputIdRef.current || activeAgentIdRef.current;
    if (streamControllerRef.current) {
      streamControllerRef.current.abort();
      stopCharPump();
      charQueueRef.current = [];
      releasePendingRef.current = true;
      setStreamingStarted(false);
      tryReleaseLoading();
    } else if (targetId) {
      stopCharPump();
      charQueueRef.current = [];
      updateAgentMessage(targetId, (m) => ({
        ...m,
        content: m.content || "Ответ остановлен.",
        status: "stopped"
      }));
      setLoading(false);
      releasePendingRef.current = false;
      currentOutputIdRef.current = null;
      setStreamingStarted(false);
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
            inputDisabled={loading && !streamingStarted}
            sendDisabled={loading}
            streaming={loading}
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
