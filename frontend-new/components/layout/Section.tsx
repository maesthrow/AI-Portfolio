"use client";

import { motion } from "framer-motion";
import clsx from "clsx";

type SectionProps = {
  id?: string;
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  className?: string;
};

export default function Section({ id, title, subtitle, children, className }: SectionProps) {
  return (
    <motion.section
      id={id}
      className={clsx("relative mt-24 mb-12 scroll-mt-28", className)}
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.65, ease: "easeOut", delay: 0.05 }}
      viewport={{ once: true, amount: 0.3 }}
    >
      <div className="mb-8 space-y-3">
        <p className="font-mono text-xs uppercase tracking-[0.3em] text-accent-soft">
          &gt;_ {title}
        </p>
        <h2 className="w-fit border-b-2 border-[#00ffc3] pb-2 text-4xl font-semibold tracking-wide text-slate-50">
          {title}
        </h2>
        {subtitle ? (
          <p className="max-w-3xl text-lg leading-relaxed text-gray-300">{subtitle}</p>
        ) : null}
      </div>
      {children}
    </motion.section>
  );
}
