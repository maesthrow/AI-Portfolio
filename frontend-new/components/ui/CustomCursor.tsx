"use client";

import { useEffect, useRef, useState, useCallback } from "react";

interface Point {
  x: number;
  y: number;
}

interface TrailPoint extends Point {
  timestamp: number;
}

export default function CustomCursor() {
  const [position, setPosition] = useState<Point>({ x: 0, y: 0 });
  const [velocity, setVelocity] = useState(0);
  const [isVisible, setIsVisible] = useState(false);
  const [isPointer, setIsPointer] = useState(false);
  const [isClicking, setIsClicking] = useState(false);
  const [trail, setTrail] = useState<TrailPoint[]>([]);
  const [isTouchDevice, setIsTouchDevice] = useState(false);
  const [hasInteracted, setHasInteracted] = useState(false);
  const [reducedMotion, setReducedMotion] = useState(false);
  const [clickRipple, setClickRipple] = useState<{ x: number; y: number; id: number } | null>(null);

  const lastPosRef = useRef<Point>({ x: 0, y: 0 });
  const lastTimeRef = useRef(0);
  const rafRef = useRef<number>();
  const rippleIdRef = useRef(0);
  const touchStartRef = useRef<Point | null>(null);
  const touchMovedRef = useRef(false);
  const touchHideTimeoutRef = useRef<number | null>(null);

  // Detect reduced motion preference
  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReducedMotion(mq.matches);

    const handler = (e: MediaQueryListEvent) => setReducedMotion(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  // Mouse movement handler with velocity calculation
  useEffect(() => {
    const handlePointerMove = (e: PointerEvent) => {
      const isTouchLike =
        e.pointerType === "touch" ||
        e.pointerType === "pen" ||
        window.matchMedia("(pointer: coarse)").matches;

      // On touch/pen we don't reposition cursor while moving (e.g., scrolling)
      if (isTouchLike && touchStartRef.current) {
        const dx = e.clientX - touchStartRef.current.x;
        const dy = e.clientY - touchStartRef.current.y;
        if (dx * dx + dy * dy > 12 * 12) {
          touchMovedRef.current = true;
        }
        return;
      }

      const now = performance.now();
      const dt = now - lastTimeRef.current;

      // Throttle to ~60fps
      if (dt < 16) return;

      const dx = e.clientX - lastPosRef.current.x;
      const dy = e.clientY - lastPosRef.current.y;
      const dist = Math.sqrt(dx * dx + dy * dy);
      const vel = Math.min((dist / dt) * 50, 1); // Normalized velocity 0-1

      lastPosRef.current = { x: e.clientX, y: e.clientY };
      lastTimeRef.current = now;

      setIsTouchDevice(isTouchLike);
      setPosition({ x: e.clientX, y: e.clientY });
      setVelocity(vel);
      setIsVisible(true);

      // Add to trail (only if motion is not reduced)
      if (!reducedMotion) {
        setTrail((prev) => {
          const newTrail = [
            { x: e.clientX, y: e.clientY, timestamp: now },
            ...prev.slice(0, 15),
          ];
          return newTrail;
        });
      }
    };

    const handlePointerEnter = () => setIsVisible(true);
    const handlePointerLeave = () => {
      if (isTouchDevice && hasInteracted) return;
      setIsVisible(false);
    };

    window.addEventListener("pointermove", handlePointerMove, { passive: true });
    document.addEventListener("pointerenter", handlePointerEnter);
    document.addEventListener("pointerleave", handlePointerLeave);

    return () => {
      window.removeEventListener("pointermove", handlePointerMove);
      document.removeEventListener("pointerenter", handlePointerEnter);
      document.removeEventListener("pointerleave", handlePointerLeave);
    };
  }, [reducedMotion, isTouchDevice, hasInteracted]);

  // Detect pointer cursor on elements
  useEffect(() => {
    const handlePointerOver = (e: PointerEvent) => {
      const target = e.target as HTMLElement;
      const isClickable =
        target.tagName === "A" ||
        target.tagName === "BUTTON" ||
        target.closest("a") !== null ||
        target.closest("button") !== null ||
        target.getAttribute("role") === "button" ||
        window.getComputedStyle(target).cursor === "pointer";

      setIsPointer(isClickable);
    };

    window.addEventListener("pointerover", handlePointerOver, { passive: true });
    return () => window.removeEventListener("pointerover", handlePointerOver);
  }, []);

  // Click handlers
  useEffect(() => {
    const handlePointerDown = (e: PointerEvent) => {
      const isTouchLike =
        e.pointerType === "touch" ||
        e.pointerType === "pen" ||
        window.matchMedia("(pointer: coarse)").matches;

      if (touchHideTimeoutRef.current !== null) {
        window.clearTimeout(touchHideTimeoutRef.current);
        touchHideTimeoutRef.current = null;
      }

      setIsTouchDevice(isTouchLike);
      setHasInteracted(true);
      setIsClicking(true);
      setIsVisible(true);

      if (isTouchLike) {
        touchStartRef.current = { x: e.clientX, y: e.clientY };
        touchMovedRef.current = false;
        setPosition({ x: e.clientX, y: e.clientY });
      } else {
        setPosition({ x: e.clientX, y: e.clientY });
      }

      // Add ripple effect
      if (!reducedMotion) {
        const id = rippleIdRef.current++;
        setClickRipple({ x: e.clientX, y: e.clientY, id });

        setTimeout(() => {
          setClickRipple((current) => (current?.id === id ? null : current));
        }, 400);
      }
    };

    const handlePointerUp = (e: PointerEvent) => {
      setIsClicking(false);

      const isTouchLike =
        e.pointerType === "touch" ||
        e.pointerType === "pen" ||
        window.matchMedia("(pointer: coarse)").matches;

      if (isTouchLike) {
        if (!touchMovedRef.current) {
          setPosition({ x: e.clientX, y: e.clientY });
          setIsVisible(true);
          touchHideTimeoutRef.current = window.setTimeout(() => {
            setIsVisible(false);
          }, 450);
        }
        touchStartRef.current = null;
        touchMovedRef.current = false;
      }
    };

    window.addEventListener("pointerdown", handlePointerDown);
    window.addEventListener("pointerup", handlePointerUp);

    return () => {
      window.removeEventListener("pointerdown", handlePointerDown);
      window.removeEventListener("pointerup", handlePointerUp);
    };
  }, [reducedMotion]);

  // Trail cleanup animation loop
  useEffect(() => {
    if (reducedMotion) return;

    const animate = () => {
      const now = performance.now();
      setTrail((prev) => prev.filter((p) => now - p.timestamp < 180));
      rafRef.current = requestAnimationFrame(animate);
    };

    rafRef.current = requestAnimationFrame(animate);
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, [isTouchDevice, reducedMotion]);

  const now = typeof performance !== "undefined" ? performance.now() : 0;

  return (
    <>
      {/* Click ripple effect */}
      {clickRipple && (
        <div
          key={clickRipple.id}
          className="fixed pointer-events-none z-[9997] rounded-full animate-cursor-ripple"
          style={{
            left: clickRipple.x,
            top: clickRipple.y,
            width: 8,
            height: 8,
            transform: "translate(-50%, -50%)",
            border: "1.5px solid rgba(0, 255, 195, 0.55)",
            boxShadow: "0 0 8px rgba(0, 255, 195, 0.35)",
          }}
        />
      )}

      {/* Trail dots - opacity based on velocity and age */}
      {!reducedMotion &&
        trail.map((point, i) => {
          const age = (now - point.timestamp) / 220;
          const baseOpacity = Math.max(0, (1 - age) * 0.7);
          const velocityMultiplier = 0.5 + velocity * 0.5;
          const opacity = baseOpacity * velocityMultiplier;
          const size = Math.max(4, 10 - i * 0.35);

          if (opacity < 0.05) return null;

          return (
            <div
              key={`${point.timestamp}-${i}`}
              className="fixed pointer-events-none z-[9998] rounded-full"
              style={{
                left: point.x,
                top: point.y,
                width: size,
                height: size,
                opacity,
                transform: "translate(-50%, -50%)",
                backgroundColor: `rgba(0, 255, 195, ${0.6 - i * 0.025})`,
                boxShadow:
                  i < 6
                    ? `0 0 ${8 - i}px rgba(0, 255, 195, ${0.5 - i * 0.07})`
                    : "none",
              }}
            />
          );
        })}

      {(!isTouchDevice || (isTouchDevice && isVisible)) && (
        <>
          {/* Main cursor ring */}
          <div
            className={`fixed pointer-events-none z-[9999] rounded-full border-2 ${
              isVisible ? "opacity-100" : "opacity-0"
            } ${!isClicking ? "cursor-breathe" : ""}`}
            style={{
              left: position.x,
              top: position.y,
              width: isPointer ? 24 : 20,
              height: isPointer ? 24 : 20,
              transform: `translate(-50%, -50%) scale(${isClicking ? 0.85 : 1})`,
              borderColor: isClicking ? "rgba(0, 255, 195, 1)" : "rgba(0, 255, 195, 0.8)",
              boxShadow: isClicking
                ? "0 0 15px rgba(0, 255, 195, 0.7), 0 0 30px rgba(0, 255, 195, 0.4), inset 0 0 12px rgba(0, 255, 195, 0.2)"
                : "0 0 10px rgba(0, 255, 195, 0.5), 0 0 20px rgba(0, 255, 195, 0.3), inset 0 0 10px rgba(0, 255, 195, 0.1)",
              backgroundColor: isClicking
                ? "rgba(0, 255, 195, 0.15)"
                : isPointer
                  ? "rgba(0, 255, 195, 0.1)"
                  : "transparent",
              transition: "width 0.1s ease-out, height 0.1s ease-out, transform 0.1s ease-out, background-color 0.1s ease-out, border-color 0.1s ease-out, box-shadow 0.1s ease-out",
            }}
          />

          {/* Center dot */}
          <div
            className={`fixed pointer-events-none z-[9999] rounded-full bg-[#00ffc3] ${
              isVisible ? "opacity-100" : "opacity-0"
            }`}
            style={{
              left: position.x,
              top: position.y,
              width: isClicking ? 6 : 4,
              height: isClicking ? 6 : 4,
              transform: "translate(-50%, -50%)",
              boxShadow: isClicking
                ? "0 0 10px rgba(0, 255, 195, 1), 0 0 20px rgba(0, 255, 195, 0.5)"
                : "0 0 6px rgba(0, 255, 195, 0.8)",
              transition: "width 0.1s ease-out, height 0.1s ease-out, box-shadow 0.1s ease-out",
            }}
          />
        </>
      )}
    </>
  );
}

// Breathing effect for static cursor (desktop only)
// Applied when not clicking to keep the glow subtle but alive.
if (typeof window !== "undefined") {
  const styleId = "custom-cursor-breathe-style";
  if (!document.getElementById(styleId)) {
    const style = document.createElement("style");
    style.id = styleId;
    style.textContent = `
      @keyframes cursor-breathe {
        0% { transform: translate(-50%, -50%) scale(1); box-shadow: 0 0 12px rgba(0,255,195,0.55), 0 0 22px rgba(0,255,195,0.32), inset 0 0 12px rgba(0,255,195,0.12); }
        50% { transform: translate(-50%, -50%) scale(1.06); box-shadow: 0 0 18px rgba(0,255,195,0.6), 0 0 30px rgba(0,255,195,0.4), inset 0 0 14px rgba(0,255,195,0.14); }
        100% { transform: translate(-50%, -50%) scale(1); box-shadow: 0 0 12px rgba(0,255,195,0.55), 0 0 22px rgba(0,255,195,0.32), inset 0 0 12px rgba(0,255,195,0.12); }
      }
      .cursor-breathe {
        animation: cursor-breathe 2.2s ease-in-out infinite;
      }
    `;
    document.head.appendChild(style);
  }
}
