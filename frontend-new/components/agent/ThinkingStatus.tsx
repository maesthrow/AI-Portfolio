"use client";

import { useEffect, useRef, useState } from "react";

export type StatusEntry = {
  stage: string;
  text: string;
};

type ThinkingStatusProps = {
  /** Latest status received from the backend stream. `null` = hide. */
  status: StatusEntry | null;
};

/** Minimum time (ms) a status is displayed before the next one replaces it. */
const MIN_DISPLAY_MS = 800;
/** Duration (ms) of the CSS fade transition. */
const FADE_MS = 200;

/**
 * Displays pipeline stage status below the agent message bubble.
 *
 * Features:
 * - Min-duration queue: fast statuses don't flicker (800 ms minimum).
 * - Crossfade animation between statuses.
 * - Fade-out when status is cleared (first delta or end).
 */
export default function ThinkingStatus({ status }: ThinkingStatusProps) {
  // What is currently rendered on screen.
  const [visible, setVisible] = useState<StatusEntry | null>(null);
  // Is the text fading out (opacity 0)?
  const [fading, setFading] = useState(false);

  // Queue of pending statuses not yet shown.
  const queueRef = useRef<StatusEntry[]>([]);
  // Timestamp when current status was shown.
  const shownAtRef = useRef<number>(0);
  // Timer id for deferred transitions.
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clearTimer = () => {
    if (timerRef.current !== null) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  };

  /** Show next entry from the queue, or hide if empty. */
  const showNext = () => {
    clearTimer();
    const next = queueRef.current.shift();
    if (next) {
      setFading(true);
      timerRef.current = setTimeout(() => {
        setVisible(next);
        setFading(false);
        shownAtRef.current = Date.now();
        scheduleNext();
      }, FADE_MS);
    } else {
      // Nothing queued — stay with current status until a new one or null.
    }
  };

  /** Schedule transition to next status respecting MIN_DISPLAY_MS. */
  const scheduleNext = () => {
    if (queueRef.current.length === 0) return;
    clearTimer();
    const elapsed = Date.now() - shownAtRef.current;
    const delay = Math.max(0, MIN_DISPLAY_MS - elapsed);
    timerRef.current = setTimeout(showNext, delay);
  };

  // React to new incoming status.
  useEffect(() => {
    if (status === null) {
      // Backend signaled end — drain queue quickly and fade out.
      clearTimer();
      queueRef.current = [];
      setFading(true);
      timerRef.current = setTimeout(() => {
        setVisible(null);
        setFading(false);
      }, FADE_MS);
      return;
    }

    if (visible === null) {
      // Nothing displayed yet — show immediately.
      clearTimer();
      queueRef.current = [];
      setVisible(status);
      setFading(false);
      shownAtRef.current = Date.now();
    } else {
      // Already displaying something — enqueue and schedule.
      queueRef.current.push(status);
      if (timerRef.current === null) {
        scheduleNext();
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status]);

  // Cleanup on unmount.
  useEffect(() => {
    return () => clearTimer();
  }, []);

  if (!visible) return null;

  return (
    <div
      className="flex items-center gap-1.5 pl-1 pt-1"
      style={{
        opacity: fading ? 0 : 1,
        transition: `opacity ${FADE_MS}ms ease-in-out`,
      }}
    >
      <span
        className="inline-block h-2.5 w-2.5 rounded-full border border-accent-soft/50 border-t-transparent animate-spin"
        style={{ animationDuration: "1.6s" }}
      />
      <span className="font-mono text-[11px] text-accent-soft/70 select-none">
        {visible.text}
      </span>
    </div>
  );
}
