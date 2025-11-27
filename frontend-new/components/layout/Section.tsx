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
      className={clsx("mb-14 scroll-mt-24", className)}
      initial={{ opacity: 0, y: 24 }}
      whileInView={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
      viewport={{ once: true, amount: 0.25 }}
    >
      <div className="mb-6">
        <p className="font-mono text-sm uppercase tracking-[0.25em] text-accent-soft">
          &gt;_ {title}
        </p>
        <div className="mt-3 h-[2px] w-16 bg-gradient-to-r from-accent to-transparent" />
        {subtitle ? <p className="mt-3 max-w-3xl text-sm text-slate-300">{subtitle}</p> : null}
      </div>
      {children}
    </motion.section>
  );
}
