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

/** Duration (ms) of the CSS fade transition between statuses. */
const FADE_MS = 150;

/**
 * Displays pipeline stage status below the agent message bubble.
 *
 * "Latest wins" strategy: always shows the most recent status immediately
 * with a short crossfade. No queue, no minimum display time — ensures
 * the user always sees the current pipeline stage, even when stages
 * complete rapidly (e.g., deterministic answers).
 */
export default function ThinkingStatus({ status }: ThinkingStatusProps) {
  // What is currently rendered on screen.
  const [visible, setVisible] = useState<StatusEntry | null>(null);
  // Is the text fading out (opacity 0)?
  const [fading, setFading] = useState(false);
  // Timer id for deferred transitions.
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clearTimer = () => {
    if (timerRef.current !== null) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  };

  // React to new incoming status.
  useEffect(() => {
    if (status === null) {
      // Backend signaled end — fade out current status.
      clearTimer();
      setFading(true);
      timerRef.current = setTimeout(() => {
        setVisible(null);
        setFading(false);
      }, FADE_MS);
      return;
    }

    if (visible === null) {
      // Nothing displayed yet — show immediately (no animation).
      clearTimer();
      setVisible(status);
      setFading(false);
    } else {
      // Already displaying something — crossfade to the new status.
      clearTimer();
      setFading(true);
      timerRef.current = setTimeout(() => {
        setVisible(status);
        setFading(false);
      }, FADE_MS);
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
        className="inline-block h-1.5 w-1.5 rounded-full bg-accent-soft/60 animate-[breathe_2s_ease-in-out_infinite]"
      />
      <span className="font-mono text-[11px] text-accent-soft/70 select-none">
        {visible.text}
      </span>
    </div>
  );
}
