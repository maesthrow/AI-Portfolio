"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import clsx from "clsx";

import AgentChatWindow from "@/components/agent/AgentChatWindow";
import { StatusEntry } from "@/components/agent/ThinkingStatus";
import { callAgentStream, ChatStreamEvent, getRateLimitStatus, isRateLimitError } from "@/lib/api";
import { AgentMessage, RateLimitInfo, RateLimitError } from "@/lib/types";

const HINT_KEY = "hasSeenAgentHint_v2";
const HINT_TTL_MS = 7 * 24 * 60 * 60 * 1000; // 7 дней

/**
 * Преобразует техническое сообщение об ошибке в понятное пользователю.
 */
function getUserFriendlyErrorMessage(technicalMessage: string): string {
  const lower = technicalMessage.toLowerCase();

  // Таймаут
  if (lower.includes("timeout") || lower.includes("timed out") || lower.includes("таймаут")) {
    return "Сервер не успел ответить. Попробуйте ещё раз.";
  }

  // Проблемы с сетью
  if (lower.includes("network") || lower.includes("connection") || lower.includes("fetch") || lower.includes("econnrefused")) {
    return "Не удалось подключиться к серверу. Проверьте интернет-соединение.";
  }

  // Ошибки сервера
  if (lower.includes("500") || lower.includes("502") || lower.includes("503") || lower.includes("internal server") || lower.includes("service unavailable")) {
    return "Сервер временно недоступен. Попробуйте позже.";
  }

  // LLM ошибки
  if (lower.includes("llm") || lower.includes("model") || lower.includes("gigachat") || lower.includes("openai")) {
    return "AI-модель временно недоступна. Попробуйте через несколько минут.";
  }

  // Пустой ответ
  if (lower.includes("empty") || lower.includes("no response") || lower.includes("пустой")) {
    return "Не удалось получить ответ. Попробуйте переформулировать вопрос.";
  }

  // По умолчанию — дружелюбное сообщение без технических деталей
  return "Произошла ошибка. Попробуйте ещё раз или задайте другой вопрос.";
}

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
  const [thinkingStatus, setThinkingStatus] = useState<StatusEntry | null>(null);
  // Counter incremented on every status event — immune to React batching
  // (unlike thinkingStatus which can go null→{x}→null in one batch).
  const [scrollKick, setScrollKick] = useState(0);
  const hintTimerRef = useRef<number | null>(null);
  const hintHideTimerRef = useRef<number | null>(null);

  // Rate limiting state
  const [rateLimitInfo, setRateLimitInfo] = useState<RateLimitInfo | null>(null);
  const [rateLimitError, setRateLimitError] = useState<RateLimitError | null>(null);

  // Скорость вывода символов для стрима - memoized
  const charSpeed = useMemo(() => ({
    perSecond: Number(process.env.NEXT_PUBLIC_CHARS_PER_SECOND) || 60,
    maxPerTick: Number(process.env.NEXT_PUBLIC_MAX_CHARS_PER_TICK) || 4
  }), []);

  const dismissHint = useCallback(() => {
    setHintShown(false);
    if (typeof window !== "undefined") {
      try {
        localStorage.setItem(HINT_KEY, Date.now().toString());
      } catch (e) {
        // ignore
      }
    }
    if (hintTimerRef.current) {
      clearTimeout(hintTimerRef.current);
      hintTimerRef.current = null;
    }
    if (hintHideTimerRef.current) {
      clearTimeout(hintHideTimerRef.current);
      hintHideTimerRef.current = null;
    }
  }, []);

  useEffect(() => {
    let resizeTimeout: number | null = null;
    const onResize = () => {
      if (resizeTimeout) return;
      resizeTimeout = window.setTimeout(() => {
        setIsMobile(window.innerWidth < 768);
        resizeTimeout = null;
      }, 150);
    };
    setIsMobile(window.innerWidth < 768);
    window.addEventListener("resize", onResize);

    const shouldShow = (() => {
      if (typeof window === "undefined") return false;
      try {
        const stored = localStorage.getItem(HINT_KEY);
        if (!stored) return true;
        const seenAt = Number(stored);
        if (Number.isNaN(seenAt)) return true;
        return Date.now() - seenAt > HINT_TTL_MS;
      } catch (e) {
        return true;
      }
    })();

    if (shouldShow) {
      hintTimerRef.current = window.setTimeout(() => setHintShown(true), 5500);
    }

    return () => {
      window.removeEventListener("resize", onResize);
      if (resizeTimeout) clearTimeout(resizeTimeout);
      if (hintTimerRef.current) clearTimeout(hintTimerRef.current);
      if (hintHideTimerRef.current) clearTimeout(hintHideTimerRef.current);
    };
  }, []);

  useEffect(() => {
    if (!hintShown) return;
    hintHideTimerRef.current = window.setTimeout(() => {
      dismissHint();
    }, 9000);
    return () => {
      if (hintHideTimerRef.current) clearTimeout(hintHideTimerRef.current);
    };
  }, [hintShown]);

  // Проверить rate limit статус при открытии dock
  useEffect(() => {
    if (!isOpen) return;

    const checkStatus = async () => {
      try {
        const status = await getRateLimitStatus();
        if (!status.available) {
          setRateLimitError({
            code: 'SERVICE_UNAVAILABLE',
            message: 'AI-агент временно недоступен. Попробуйте позже',
          });
        } else if (status.rate_limit?.exceeded) {
          setRateLimitError({
            code: 'RATE_LIMIT_EXCEEDED',
            message: 'Достигнут лимит использования AI-агента',
            details: {
              exceeded: true,
              reset_in_seconds: status.rate_limit.reset_in_seconds,
              reset_in_human: '',
            },
          });
        } else if (status.rate_limit?.show_warning) {
          setRateLimitInfo(status.rate_limit);
        } else {
          // Сбросить предыдущее состояние если всё ок
          setRateLimitInfo(null);
        }
      } catch (e) {
        console.error('Failed to check rate limit status:', e);
      }
    };

    checkStatus();
  }, [isOpen]);

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

  const pumpChars = useCallback((targetId: string) => {
    if (!charQueueRef.current.length) {
      frameRef.current = null;
      tryReleaseLoading();
      return;
    }

    const now = performance.now();
    const intervalMs = 1000 / charSpeed.perSecond;

    if (now - lastTickRef.current < intervalMs) {
      frameRef.current = requestAnimationFrame(() => pumpChars(targetId));
      return;
    }

    const elapsed = now - lastTickRef.current;
    lastTickRef.current = now;
    const budget = Math.max(1, Math.floor(elapsed / intervalMs));
    const take = Math.min(charSpeed.maxPerTick, budget, charQueueRef.current.length);
    const chunk = charQueueRef.current.splice(0, take).join("");

    if (chunk) {
      updateAgentMessage(targetId, (m) => ({ ...m, content: (m.content || "") + chunk }));
    }

    frameRef.current = requestAnimationFrame(() => pumpChars(targetId));
  }, [charSpeed]);

  const enqueueChars = useCallback((targetId: string, text: string) => {
    if (!text) return;
    charQueueRef.current.push(...text);
    if (!frameRef.current) {
      pumpChars(targetId);
    }
  }, [pumpChars]);

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
    setThinkingStatus(null);
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
        } else if (event.type === "status") {
          setThinkingStatus({ stage: event.stage, text: event.text });
          setScrollKick(c => c + 1);
        } else if (event.type === "delta") {
          if (!streamingStarted) {
            setStreamingStarted(true);
            setThinkingStatus(null);
            // Smooth-scroll when response starts (ThinkingStatus → text).
            // Critical for short responses (CV flow) where the instant
            // scrollTop assignment from [messages,typing] useEffect is
            // barely visible.
            setScrollKick(c => c + 1);
          }
          enqueueChars(tempId, event.content);
          updateAgentMessage(tempId, (m) => ({
            ...m,
            status: "streaming"
          }));
        } else if (event.type === "end") {
          // Обновить rate limit info если есть
          if (event.rate_limit) {
            if (event.rate_limit.show_warning) {
              setRateLimitInfo(event.rate_limit);
            } else {
              setRateLimitInfo(null);
            }
            // Проверить не превышен ли лимит после этого запроса
            if (event.rate_limit.exceeded) {
              setRateLimitError({
                code: 'RATE_LIMIT_EXCEEDED',
                message: 'Достигнут лимит использования AI-агента',
                details: {
                  exceeded: true,
                  reset_in_seconds: event.rate_limit.reset_in_seconds,
                  reset_in_human: '',
                },
              });
            }
          }
        } else if (event.type === "error") {
          applyError(getUserFriendlyErrorMessage(event.message || "unknown error"));
        }
      }

      updateAgentMessage(tempId, (m) => ({
        ...m,
        status: m.status === "error" ? m.status : "done"
      }));
      // Ensure scroll after stream completes (especially for short CV responses
      // where the entire answer arrives as a single delta).
      setScrollKick(c => c + 1);
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
      } else if (isRateLimitError(err)) {
        // Rate limit ошибка - не делаем fallback, показываем блокировку
        setRateLimitError(err);
        setMessages(prev => prev.filter(m => m.id !== tempId && m.tempId !== tempId));
        stopCharPump();
        charQueueRef.current = [];
        setLoading(false);
        setStreamingStarted(false);
        releasePendingRef.current = false;
      } else {
        applyError(getUserFriendlyErrorMessage(err?.message || "unknown error"));
        releasePendingRef.current = true;
        tryReleaseLoading();
      }
    } finally {
      streamControllerRef.current = null;
      activeAgentIdRef.current = null;
      setThinkingStatus(null);
      if (!charQueueRef.current.length) {
        stopCharPump();
        tryReleaseLoading();
      }
    }
  };

  const handleStop = () => {
    const targetId = currentOutputIdRef.current || activeAgentIdRef.current;
    setThinkingStatus(null);
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

  const handleToggle = useCallback(() => {
    setIsOpen((v) => {
      if (!v) {
        // При открытии сбрасываем ошибку, статус проверится заново в useEffect
        setRateLimitError(null);
      }
      return !v;
    });
    dismissHint();
  }, [dismissHint]);

  // Проверить статус rate limit (для кнопки "Проверить доступность" и авто-проверки)
  const handleRateLimitRetry = useCallback(async () => {
    try {
      const status = await getRateLimitStatus();

      if (!status.available) {
        // Всё ещё недоступен
        setRateLimitError({
          code: 'SERVICE_UNAVAILABLE',
          message: 'AI-агент временно недоступен. Попробуйте позже',
        });
      } else if (status.rate_limit?.exceeded) {
        // Лимит всё ещё превышен - обновить время
        setRateLimitError({
          code: 'RATE_LIMIT_EXCEEDED',
          message: 'Достигнут лимит использования AI-агента',
          details: {
            exceeded: true,
            reset_in_seconds: status.rate_limit.reset_in_seconds,
            reset_in_human: '',
          },
        });
      } else {
        // Разблокировано!
        setRateLimitError(null);
        if (status.rate_limit?.show_warning) {
          setRateLimitInfo(status.rate_limit);
        } else {
          setRateLimitInfo(null);
        }
      }
    } catch (e) {
      console.error('Failed to check rate limit status:', e);
    }
  }, []);

  // Retry сообщения пользователя (без добавления нового user message)
  const handleMessageRetry = useCallback(async (question: string) => {
    if (loading || rateLimitError) return;

    const sessionId = sessionIdRef.current;
    const tempId = `${Date.now()}-agent`;

    const agentPlaceholder: AgentMessage = {
      id: tempId,
      tempId,
      role: "agent",
      content: "",
      createdAt: Date.now(),
      status: "streaming"
    };

    setMessages((prev) => [...prev, agentPlaceholder]);
    setLoading(true);
    setStreamingStarted(false);
    setThinkingStatus(null);
    releasePendingRef.current = false;

    const controller = new AbortController();
    streamControllerRef.current = controller;

    activeAgentIdRef.current = tempId;
    currentOutputIdRef.current = tempId;
    charQueueRef.current = [];
    stopCharPump();

    try {
      const stream = await callAgentStream(
        { question, session_id: sessionId },
        { signal: controller.signal }
      );

      for await (const event of stream as AsyncIterable<ChatStreamEvent>) {
        if (event.type === "start" && event.message_id) {
          currentOutputIdRef.current = event.message_id;
          updateAgentMessage(tempId, (m) => ({ ...m, id: event.message_id }));
        } else if (event.type === "status") {
          setThinkingStatus({ stage: event.stage, text: event.text });
          setScrollKick(c => c + 1);
        } else if (event.type === "delta") {
          if (!streamingStarted) {
            setStreamingStarted(true);
            setThinkingStatus(null);
            // Smooth-scroll when response starts (ThinkingStatus → text).
            // Critical for short responses (CV flow) where the instant
            // scrollTop assignment from [messages,typing] useEffect is
            // barely visible.
            setScrollKick(c => c + 1);
          }
          enqueueChars(tempId, event.content);
          updateAgentMessage(tempId, (m) => ({
            ...m,
            status: "streaming"
          }));
        } else if (event.type === "end") {
          if (event.rate_limit) {
            if (event.rate_limit.show_warning) {
              setRateLimitInfo(event.rate_limit);
            } else {
              setRateLimitInfo(null);
            }
            if (event.rate_limit.exceeded) {
              setRateLimitError({
                code: 'RATE_LIMIT_EXCEEDED',
                message: 'Достигнут лимит использования AI-агента',
                details: {
                  exceeded: true,
                  reset_in_seconds: event.rate_limit.reset_in_seconds,
                  reset_in_human: '',
                },
              });
            }
          }
        } else if (event.type === "error") {
          updateAgentMessage(tempId, (m) => ({
            ...m,
            content: getUserFriendlyErrorMessage(event.message || "unknown error"),
            status: "error"
          }));
        }
      }

      updateAgentMessage(tempId, (m) => ({
        ...m,
        status: m.status === "error" ? m.status : "done"
      }));
      // Ensure scroll after stream completes (especially for short CV responses
      // where the entire answer arrives as a single delta).
      setScrollKick(c => c + 1);
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
      } else if (isRateLimitError(err)) {
        setRateLimitError(err);
        setMessages(prev => prev.filter(m => m.id !== tempId && m.tempId !== tempId));
      } else {
        updateAgentMessage(tempId, (m) => ({
          ...m,
          content: "Не получилось связаться с агентом. Попробуйте позже.",
          status: "error"
        }));
      }
      releasePendingRef.current = true;
      tryReleaseLoading();
    } finally {
      streamControllerRef.current = null;
      activeAgentIdRef.current = null;
      setThinkingStatus(null);
      if (!charQueueRef.current.length) {
        stopCharPump();
        tryReleaseLoading();
      }
    }
  }, [loading, rateLimitError, enqueueChars, streamingStarted]);

  const buttonLabel = "AI-агент";

  return (
    <div className="pointer-events-none fixed bottom-4 right-4 z-50 flex flex-col items-end gap-3">
      <button
        onClick={handleToggle}
        className="pointer-events-auto flex items-center gap-3 rounded-full border border-accent/40 bg-gradient-to-r from-accent/20 via-accent-soft/20 to-accent/10 px-4 py-2 text-sm font-semibold text-slate-100 shadow-neon transition-all duration-200 hover:-translate-y-0.5 hover:shadow-neon-strong focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60 animate-[dockPulse_3.6s_ease-in-out_infinite]"
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
            streamingStarted={streamingStarted}
            inputDisabled={loading && !streamingStarted}
            sendDisabled={loading}
            streaming={loading}
            onStop={handleStop}
            thinkingStatus={thinkingStatus}
            scrollKick={scrollKick}
            rateLimitInfo={rateLimitInfo}
            rateLimitError={rateLimitError}
            onRateLimitRetry={handleRateLimitRetry}
            onMessageRetry={handleMessageRetry}
            isMobile={isMobile}
          />
        </div>
      ) : null}

      {!isOpen && hintShown ? (
        <div className="pointer-events-none mb-1 rounded-xl border border-accent/40 bg-black/80 px-3 py-2 text-xs text-slate-100 shadow-neon">
          Спроси агента о проектах или опыте
        </div>
      ) : null}

      <style jsx>{`
        @keyframes dockPulse {
          0%,
          100% {
            box-shadow: 0 0 16px rgba(0, 255, 200, 0.35), 0 0 0 0 rgba(0, 255, 200, 0.16);
          }
          50% {
            box-shadow: 0 0 28px rgba(0, 255, 200, 0.48), 0 0 30px 6px rgba(0, 255, 200, 0.18);
          }
        }
      `}</style>
    </div>
  );
}
