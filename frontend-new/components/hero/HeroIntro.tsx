"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import Section from "@/components/layout/Section";
import { Contact, Profile } from "@/lib/types";

type HeroIntroProps = {
  profile: Profile;
  contacts: Contact[];
};

const primaryContacts: Contact["kind"][] = ["github", "telegram", "linkedin", "other"];
const defaultName = "Дмитрий Каргин";
const heroLabel = "AI-Portfolio — портфолио будущего";
const heroSubheadline = "ML / LLM Engineer";
const heroDescription =
  "Создаю готовые AI-системы и решения для реальных сервисов.";
const heroTags = ["AI-agents", "LLM", "RAG", "CV", "MLOps", "Backend"];
const scrollHint = "листай дальше";

function contactLink(contacts: Contact[], kind: Contact["kind"]) {
  return contacts.find((c) => c.kind === kind);
}

export default function HeroIntro({ profile, contacts }: HeroIntroProps) {
  const avatar =
    profile.avatarUrl ?? (profile as any).avatar_url ?? (profile as any).avatar ?? null;
  const hasAvatar = Boolean(avatar);
  const displayName = profile.name || defaultName;

  return (
    <Section
      id="hero"
      label={heroLabel}
      title=""
      className="!mt-6 pt-0 sm:!mt-8 sm:pt-3 md:!mt-12 lg:!mt-16 [&>div>h2]:hidden [&>div]:mb-4 sm:[&>div]:mb-6 md:[&>div]:mb-8 [&>div>p]:normal-case"
    >
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, ease: "easeOut" }}
        className="relative overflow-hidden rounded-3xl border border-[#00ffc3]/25 bg-gradient-to-br from-bg-panel/80 via-black/60 to-bg-panel/80 p-6 shadow-[0_0_35px_rgba(0,255,200,0.35)] backdrop-blur sm:p-9 md:p-12 lg:p-14"
      >
        <div className="pointer-events-none absolute inset-0 opacity-70">
          <div className="absolute inset-0 animate-[glowDrift_22s_ease-in-out_infinite] bg-[radial-gradient(circle_at_30%_30%,rgba(0,255,195,0.12),transparent_35%)]" />
          <div className="absolute inset-0 animate-[gridShift_28s_linear_infinite] bg-[linear-gradient(90deg,rgba(0,255,195,0.08)_1px,transparent_1px),linear-gradient(0deg,rgba(0,255,195,0.08)_1px,transparent_1px)] bg-[size:40px_40px] opacity-30" />
          <div className="absolute inset-0 animate-[glowDrift_18s_ease-in-out_infinite] bg-[radial-gradient(circle_at_70%_60%,rgba(139,92,246,0.18),transparent_45%)]" />
        </div>
        <div className="relative grid gap-6 sm:gap-8 md:grid-cols-[1.35fr,1fr] md:items-center md:gap-10 lg:grid-cols-[3fr,2fr]">
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, ease: "easeOut", delay: 0.1 }}
            className="space-y-4 sm:space-y-5 md:space-y-6"
          >
            <p className="flex items-center gap-2 font-mono text-base text-accent-soft sm:text-lg">
              <span className="inline-flex items-center rounded-full border border-[#19f0c3]/60 bg-[#19f0c3]/10 px-3 py-1 text-sm font-semibold text-[#19f0c3] sm:text-base">
                {heroSubheadline}
              </span>
            </p>
            <h1 className="text-4xl font-bold leading-tight text-slate-50 sm:text-5xl lg:text-6xl">
              {displayName}
            </h1>
            <p className="max-w-2xl text-left text-base leading-relaxed text-slate-100 sm:text-lg md:max-w-3xl">
              {heroDescription}
            </p>
            <div className="flex max-w-2xl flex-wrap gap-2 text-sm font-medium text-gray-200 sm:gap-2.5">
              {heroTags.map((tag) => (
                <span
                  key={tag}
                  className="rounded-full border border-accent/30 bg-white/5 px-3 py-1 leading-tight"
                >
                  {tag}
                </span>
              ))}
            </div>
            <div className="flex flex-wrap gap-3 sm:gap-4">
              {primaryContacts.map((kind) => {
                const item = contactLink(contacts, kind);
                if (!item) return null;
                return (
                  <Link
                    key={kind}
                    href={item.url}
                    className="group inline-flex items-center gap-2 rounded-full border border-[#00ffc3]/50 bg-black/40 px-5 py-2.5 text-sm font-semibold text-slate-100 shadow-[0_0_25px_rgba(0,255,200,0.25)] transition duration-200 hover:-translate-y-1 hover:scale-105 hover:border-[#00ffc3]/70 hover:shadow-[0_0_45px_rgba(0,255,200,0.35)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/50"
                    target="_blank"
                    rel="noreferrer"
                  >
                    <span className="h-2 w-2 rounded-full bg-accent-soft shadow-[0_0_12px_rgba(0,255,200,0.6)] transition group-hover:shadow-[0_0_18px_rgba(0,255,200,0.8)]" />
                    {item.label}
                  </Link>
                );
              })}
            </div>
          </motion.div>
          <motion.div
            initial={{ opacity: 0, y: 32 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.9, ease: "easeOut", delay: 0.15 }}
            className="relative flex h-full items-center justify-center"
          >
            <div className="relative h-48 w-48 overflow-hidden rounded-3xl border border-[#00ffc3]/40 bg-gradient-to-br from-accent/15 via-accent-alt/10 to-transparent shadow-[0_0_35px_rgba(0,255,200,0.3)] sm:h-56 sm:w-56 md:h-64 md:w-64">
              {hasAvatar ? (
                <img src={avatar} alt={displayName || "avatar"} className="h-full w-full object-cover" />
              ) : (
                <>
                  <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_20%,rgba(34,240,192,0.4),transparent_35%),radial-gradient(circle_at_70%_60%,rgba(139,92,246,0.25),transparent_40%)]" />
                  <div className="absolute inset-0 flex items-center justify-center font-mono text-xs uppercase text-accent-soft/80">
                    avatar
                  </div>
                </>
              )}
            </div>
          </motion.div>
        </div>
        <style jsx>{`
          @keyframes glowDrift {
            0% {
              transform: translate3d(0, 0, 0) scale(1);
            }
            50% {
              transform: translate3d(10px, -8px, 0) scale(1.01);
            }
            100% {
              transform: translate3d(0, 0, 0) scale(1);
            }
          }
          @keyframes gridShift {
            0% {
              background-position: 0 0;
            }
            100% {
              background-position: 140px 110px;
            }
          }
        `}</style>
      </motion.div>
    </Section>
  );
}
