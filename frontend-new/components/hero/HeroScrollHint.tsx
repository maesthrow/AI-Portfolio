"use client";

import { useEffect, useRef, useState } from "react";
import { ChevronDown } from "lucide-react";

type HeroScrollHintProps = {
  targetId: string;
};

export default function HeroScrollHint({ targetId }: HeroScrollHintProps) {
  const [visible, setVisible] = useState(true);
  const btnRef = useRef<HTMLButtonElement | null>(null);

  useEffect(() => {
    const onScroll = () => {
      if (!visible) return;

      // Hide once the button itself scrolls past the viewport top.
      const btn = btnRef.current;
      if (btn) {
        const rect = btn.getBoundingClientRect();
        if (rect.bottom <= 0) {
          setVisible(false);
          return;
        }
      }

      // Fallback trigger by next section position.
      const target = document.getElementById(targetId);
      const trigger = target ? Math.max(40, target.offsetTop - 8) : 200;
      if (window.scrollY >= trigger) {
        setVisible(false);
      }
    };

    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, [targetId, visible]);

  if (!visible) return null;

  const handleClick = () => {
    const el = document.getElementById(targetId);
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "start" });
    }
    setVisible(false);
  };

  return (
    <div className="pointer-events-none relative z-20 pb-[env(safe-area-inset-bottom,0px)]">
      <button
        type="button"
        onClick={handleClick}
        ref={btnRef}
        className="pointer-events-auto absolute bottom-[-5rem] left-1/2 grid h-12 w-12 -translate-x-1/2 place-items-center rounded-full border border-accent/70 bg-accent/10 text-accent shadow-[0_0_24px_rgba(16,240,160,0.45)] backdrop-blur transition hover:-translate-y-1 hover:border-accent/80 hover:bg-accent/15 hover:shadow-[0_0_32px_rgba(16,240,160,0.6)] sm:bottom-10"
      >
        <ChevronDown className="relative top-[2px] h-5 w-5 animate-bounce-slow stroke-[2.6]" aria-hidden="true" />
        <span className="sr-only">Scroll to next section</span>
      </button>
    </div>
  );
}
