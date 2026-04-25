"use client";

import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import ExperienceCard from "@/components/experience/ExperienceCard";
import { ExperienceItem } from "@/lib/types";

const VISIBLE_COUNT = 4;

type ExperienceListProps = {
  items: ExperienceItem[];
};

export default function ExperienceList({ items }: ExperienceListProps) {
  const [expanded, setExpanded] = useState(false);

  const visible = items.slice(0, VISIBLE_COUNT);
  const hidden = items.slice(VISIBLE_COUNT);
  const hasMore = hidden.length > 0;

  return (
    <>
      <div
        className="grid grid-cols-1 gap-6 lg:grid-cols-2 lg:[&>*:last-child:nth-child(odd)]:col-span-2 lg:[&>*:last-child:nth-child(odd)]:mx-auto lg:[&>*:last-child:nth-child(odd)]:w-[calc(50%-0.75rem)]"
      >
        {visible.map((item) => (
          <ExperienceCard key={item.id} item={item} />
        ))}
        <AnimatePresence initial={false}>
          {expanded &&
            hidden.map((item, idx) => (
              <motion.div
                key={item.id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 8 }}
                transition={{ duration: 0.3, delay: idx * 0.05, ease: "easeOut" }}
              >
                <ExperienceCard item={item} />
              </motion.div>
            ))}
        </AnimatePresence>
      </div>

      {hasMore ? (
        <div className="mt-8 flex justify-center">
          <button
            type="button"
            onClick={() => setExpanded((prev) => !prev)}
            aria-expanded={expanded}
            className="group/cta inline-flex items-center gap-2 rounded-full border border-[#00ffc3]/50 bg-black/50 px-5 py-2.5 text-sm font-medium text-accent transition-all duration-200 hover:-translate-y-0.5 hover:border-[#00ffc3]/80 hover:shadow-[0_0_14px_rgba(0,255,200,0.25)]"
          >
            {expanded ? (
              <>
                <span
                  aria-hidden="true"
                  className="transition-transform duration-300 group-hover/cta:-translate-x-0.5"
                >
                  &#8592;
                </span>
                <span>Свернуть</span>
              </>
            ) : (
              <>
                <span>Показать ещё ({hidden.length})</span>
                <span
                  aria-hidden="true"
                  className="transition-transform duration-300 group-hover/cta:translate-x-0.5"
                >
                  &#8594;
                </span>
              </>
            )}
          </button>
        </div>
      ) : null}
    </>
  );
}
