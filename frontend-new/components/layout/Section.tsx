"use client";

import { motion } from "framer-motion";
import clsx from "clsx";

type SectionProps = {
  id?: string;
  label?: string;
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  className?: string;
};

export default function Section({
  id,
  label,
  title,
  subtitle,
  children,
  className
}: SectionProps) {
  const eyebrow = label || title;
  const labelText = `>_ ${eyebrow}`;
  const isTitleEmpty = !title?.trim();

  const labelVariants = {
    hidden: { opacity: 1 },
    visible: {
      opacity: 1,
      transition: { staggerChildren: 0.06 }
    }
  };

  const charVariants = {
    hidden: { opacity: 0 },
    visible: { opacity: 1, transition: { duration: 0 } }
  };

  return (
    <motion.section
      id={id}
      className={clsx("relative mt-24 mb-12 scroll-mt-28", className)}
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.65, ease: "easeOut", delay: 0.05 }}
      viewport={{ once: true, amount: 0.3 }}
    >
      <div className="mb-8 space-y-2 md:space-y-3">
        <motion.div
          className={clsx(
            "inline-block pb-2",
            isTitleEmpty
              ? "text-[#19f0c3] text-sm sm:text-lg font-medium tracking-[0.18em]"
              : "text-[#19f0c3] text-3xl font-semibold sm:text-4xl"
          )}
          variants={labelVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, amount: 0.7 }}
        >
          {Array.from(labelText).map((ch, idx) => (
            <motion.span key={`${ch}-${idx}`} variants={charVariants}>
              {ch}
            </motion.span>
          ))}
          {!isTitleEmpty ? (
            <motion.div
              className="mt-1 h-[2px] bg-[#19f0c3]"
              initial={{ width: 0 }}
              whileInView={{ width: "100%" }}
              viewport={{ once: true, amount: 0.7 }}
              transition={{ duration: 1.6, ease: [0.3, 0.0, 0.2, 1] }}
            />
          ) : null}
        </motion.div>
        {!isTitleEmpty && subtitle ? (
          <p className="max-w-3xl text-left text-lg leading-relaxed text-slate-100 md:max-w-4xl">
            {subtitle}
          </p>
        ) : null}
      </div>
      {children}
    </motion.section>
  );
}
