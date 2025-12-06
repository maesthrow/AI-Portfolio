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

      // Найти целевую секцию и её заголовок
      const target = document.getElementById(targetId);
      if (!target) return;

      // Найти заголовок внутри секции (ищем h2, h3 или элемент с классом section title)
      const sectionHeader = target.querySelector('h2, h3, [class*="title"]');
      if (!sectionHeader) return;

      // Получить позицию заголовка относительно viewport
      const headerRect = sectionHeader.getBoundingClientRect();

      // Скрыть кнопку когда заголовок секции появляется в верхней части viewport
      // (когда верх заголовка пересекает центр экрана)
      if (headerRect.top < window.innerHeight * 0.6) {
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
      <div className="absolute bottom-[-5rem] left-1/2 flex -translate-x-1/2 flex-col items-center gap-2 sm:bottom-10">
        <span className="text-xs uppercase tracking-widest text-accent/60">Scroll</span>
        <button
          type="button"
          onClick={handleClick}
          ref={btnRef}
          className="pointer-events-auto grid h-12 w-12 place-items-center rounded-full border border-accent/70 bg-accent/10 text-accent shadow-[0_0_24px_rgba(16,240,160,0.45)] backdrop-blur transition hover:-translate-y-1 hover:border-accent/80 hover:bg-accent/15 hover:shadow-[0_0_32px_rgba(16,240,160,0.6)]"
        >
          <ChevronDown className="relative top-[2px] h-5 w-5 animate-bounce-slow stroke-[2.6]" aria-hidden="true" />
          <span className="sr-only">Scroll to next section</span>
        </button>
      </div>
    </div>
  );
}
