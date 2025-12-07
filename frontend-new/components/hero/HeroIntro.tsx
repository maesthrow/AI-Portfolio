"use client";

import { motion } from "framer-motion";
import { Github, Linkedin, Send, Sparkles } from "lucide-react";
import Section from "@/components/layout/Section";
import { SocialBadge, type SocialBadgeProps } from "@/components/ui/SocialBadge";
import { Contact, HeroTag, Profile } from "@/lib/types";

type HeroIntroProps = {
  profile: Profile;
  contacts: Contact[];
  heroTags?: HeroTag[];
};

const primaryContacts: Contact["kind"][] = ["github", "telegram", "linkedin", "other"];
const socialIcons: Partial<Record<Contact["kind"], SocialBadgeProps["icon"]>> = {
  github: Github,
  telegram: Send,
  linkedin: Linkedin,
  other: Sparkles
};
const defaultName = "Дмитрий Каргин";
const heroLabel = "AI-Portfolio — портфолио будущего";
const defaultHeadline = "AI/ML Engineer | Backend Developer";
const defaultDescription =
  "Строю AI-системы от модели и агента до продакшн-сервиса. Забочусь о качестве моделей и интегрирую их так, чтобы они помогали бизнесу.";
const fallbackTags = ["AI-agents", "LLM", "RAG", "CV", "MLOps", "Backend"];

function contactLink(contacts: Contact[], kind: Contact["kind"]) {
  return contacts.find((c) => c.kind === kind);
}

export default function HeroIntro({ profile, contacts, heroTags = [] }: HeroIntroProps) {
  const avatar =
    profile.avatarUrl ?? (profile as any).avatar_url ?? (profile as any).avatar ?? null;
  const hasAvatar = Boolean(avatar);
  const displayName = profile.name || defaultName;
  const headline = profile.hero_headline || defaultHeadline;
  const description = profile.hero_description || defaultDescription;
  const currentPosition = profile.current_position || profile.status || null;

  const skillTags = heroTags.filter((t) => !t.icon);
  const displayTags = skillTags.length > 0 ? skillTags.map((t) => t.name) : fallbackTags;

  return (
    <Section
      id="hero"
      label={heroLabel}
      title=""
      className="!mt-0 !mb-0 pt-0 [&>div]:mb-4 sm:[&>div]:mb-5 md:[&>div]:mb-6 [&>div>p]:normal-case [&>div:first-child]:hidden"
    >
      <div className="mb-4 md:mb-6">
        <div className="mt-1">
          <h1 className="hero-title text-3xl font-semibold tracking-tight text-accent md:text-4xl lg:text-[2.75rem]">
            AI-Portfolio
          </h1>
          <div className="hero-line mt-3 h-px w-full max-w-[720px] opacity-80" />
          <p className="hero-tagline hero-tagline-typing mt-2 text-sm text-accent/85 md:text-base">
            Портфолио со встроенным AI-агентом
          </p>
        </div>
      </div>
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, ease: "easeOut" }}
        className="relative w-full overflow-hidden rounded-3xl border border-[#00ffc3]/25 bg-gradient-to-br from-bg-panel/80 via-black/60 to-bg-panel/80 px-4 py-4 shadow-[0_0_26px_rgba(0,255,200,0.24)] backdrop-blur transition-shadow duration-500 hover:shadow-[0_0_40px_rgba(0,255,200,0.3)] sm:px-6 sm:py-6 md:px-8 md:py-8 lg:px-10 lg:py-10 xl:px-12 xl:py-12"
      >
        {/* Corner decorations */}
        <div className="pointer-events-none absolute left-0 top-0 h-4 w-4 rounded-tl-lg border-l-2 border-t-2 border-accent/50" />
        <div className="pointer-events-none absolute right-0 top-0 h-4 w-4 rounded-tr-lg border-r-2 border-t-2 border-accent/50" />
        <div className="pointer-events-none absolute bottom-0 left-0 h-4 w-4 rounded-bl-lg border-b-2 border-l-2 border-accent/50" />
        <div className="pointer-events-none absolute bottom-0 right-0 h-4 w-4 rounded-br-lg border-b-2 border-r-2 border-accent/50" />

        {/* Background gradient blobs (без grid) */}
        <div className="pointer-events-none absolute inset-0 opacity-70">
          <div className="absolute inset-0 animate-[glowDrift_22s_ease-in-out_infinite] bg-[radial-gradient(circle_at_30%_30%,rgba(0,255,195,0.12),transparent_35%)]" />
          <div className="absolute inset-0 animate-[glowDrift_18s_ease-in-out_infinite] bg-[radial-gradient(circle_at_70%_60%,rgba(139,92,246,0.18),transparent_45%)]" />
        </div>
        <div className="relative flex flex-col gap-6 sm:gap-7 md:gap-8 lg:flex-row lg:items-center lg:gap-11 xl:gap-14">
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, ease: "easeOut", delay: 0.1 }}
            className="space-y-3 sm:space-y-4 md:space-y-5"
          >
            <div className="flex items-center gap-2">
              <span className="inline-flex items-center gap-2 rounded-full border border-accent/40 bg-accent/10 px-4 py-1.5 text-[11px] font-semibold text-accent sm:text-xs md:text-sm">
                <span className="h-2 w-2 animate-pulse rounded-full bg-accent" />
                {headline}
              </span>
            </div>
            <h1 className="text-2xl font-bold leading-tight text-slate-50 sm:text-3xl md:text-4xl lg:text-5xl xl:text-6xl">
              {displayName}
            </h1>
            <p className="max-w-3xl text-left text-sm leading-relaxed text-slate-100/90 sm:text-base md:text-lg">
              {description}
            </p>
            {currentPosition && (
              <p className="text-xs font-mono text-accent-soft/80 sm:text-sm">
                Сейчас: {currentPosition}
              </p>
            )}
            <div className="flex max-w-3xl flex-wrap gap-2 pt-1 text-[11px] font-medium text-gray-200 sm:text-xs md:text-sm">
              {displayTags.map((tag) => (
                <span
                  key={tag}
                  className="rounded-full border border-accent/30 bg-white/5 px-3 py-1 leading-tight transition-all duration-300 hover:border-accent/60 hover:text-accent hover:shadow-[0_0_12px_rgba(16,240,160,0.25)]"
                >
                  {tag}
                </span>
              ))}
            </div>
            <div className="flex flex-wrap gap-2.5 pt-1 sm:gap-3 sm:pt-2">
              {primaryContacts.map((kind) => {
                const item = contactLink(contacts, kind);
                if (!item) return null;
                return (
                  <SocialBadge
                    key={kind}
                    href={item.url}
                    label={item.label}
                    icon={socialIcons[kind] ?? Sparkles}
                  />
                );
              })}
            </div>
          </motion.div>
          <motion.div
            initial={{ opacity: 0, y: 32 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.9, ease: "easeOut", delay: 0.15 }}
            className="relative flex h-full items-center justify-center lg:justify-end"
          >
            <div className="group relative h-40 w-40 overflow-hidden rounded-3xl border border-[#00ffc3]/40 bg-gradient-to-br from-accent/15 via-accent-alt/10 to-transparent shadow-[0_0_35px_rgba(0,255,200,0.3)] transition-all duration-500 hover:border-accent/60 hover:shadow-[0_0_50px_rgba(0,255,200,0.4)] sm:h-44 sm:w-44 md:h-56 md:w-56 lg:h-64 lg:w-64 xl:h-72 xl:w-72">
              {hasAvatar ? (
                <>
                  <img src={avatar} alt={displayName || "avatar"} className="h-full w-full object-cover transition-transform duration-700 group-hover:scale-105" />
                  {/* Gradient overlay для глубины */}
                  <div className="pointer-events-none absolute inset-0 z-10 bg-gradient-to-t from-black/30 to-transparent" />
                </>
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
      </motion.div>
    </Section>
  );
}
