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
  const [isTouchDevice, setIsTouchDevice] = useState(true);
  const [reducedMotion, setReducedMotion] = useState(false);
  const [clickRipple, setClickRipple] = useState<{ x: number; y: number; id: number } | null>(null);

  const lastPosRef = useRef<Point>({ x: 0, y: 0 });
  const lastTimeRef = useRef(0);
  const rafRef = useRef<number>();
  const rippleIdRef = useRef(0);

  // Detect touch device on mount
  useEffect(() => {
    const checkTouchDevice = () => {
      const isTouchCapable =
        "ontouchstart" in window ||
        navigator.maxTouchPoints > 0 ||
        window.matchMedia("(pointer: coarse)").matches;
      setIsTouchDevice(isTouchCapable);
    };

    checkTouchDevice();
  }, []);

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
    if (isTouchDevice) return;

    const handleMouseMove = (e: MouseEvent) => {
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

    const handleMouseEnter = () => setIsVisible(true);
    const handleMouseLeave = () => setIsVisible(false);

    window.addEventListener("mousemove", handleMouseMove, { passive: true });
    document.addEventListener("mouseenter", handleMouseEnter);
    document.addEventListener("mouseleave", handleMouseLeave);

    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseenter", handleMouseEnter);
      document.removeEventListener("mouseleave", handleMouseLeave);
    };
  }, [isTouchDevice, reducedMotion]);

  // Detect pointer cursor on elements
  useEffect(() => {
    if (isTouchDevice) return;

    const handleMouseOver = (e: MouseEvent) => {
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

    window.addEventListener("mouseover", handleMouseOver, { passive: true });
    return () => window.removeEventListener("mouseover", handleMouseOver);
  }, [isTouchDevice]);

  // Click handlers
  useEffect(() => {
    if (isTouchDevice) return;

    const handleMouseDown = (e: MouseEvent) => {
      setIsClicking(true);

      // Add ripple effect
      if (!reducedMotion) {
        const id = rippleIdRef.current++;
        setClickRipple({ x: e.clientX, y: e.clientY, id });

        setTimeout(() => {
          setClickRipple((current) => (current?.id === id ? null : current));
        }, 400);
      }
    };

    const handleMouseUp = () => setIsClicking(false);

    window.addEventListener("mousedown", handleMouseDown);
    window.addEventListener("mouseup", handleMouseUp);

    return () => {
      window.removeEventListener("mousedown", handleMouseDown);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isTouchDevice, reducedMotion]);

  // Trail cleanup animation loop
  useEffect(() => {
    if (isTouchDevice || reducedMotion) return;

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

  // Don't render on touch devices
  if (isTouchDevice) return null;

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
            width: 10,
            height: 10,
            transform: "translate(-50%, -50%)",
            border: "2px solid rgba(0, 255, 195, 0.7)",
            boxShadow: "0 0 10px rgba(0, 255, 195, 0.5)",
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

      {/* Main cursor ring */}
      <div
        className={`fixed pointer-events-none z-[9999] rounded-full border-2 ${
          isVisible ? "opacity-100" : "opacity-0"
        }`}
        style={{
          left: position.x,
          top: position.y,
          width: isPointer ? 28 : 24,
          height: isPointer ? 28 : 24,
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
  );
}
