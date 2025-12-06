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
  other: Sparkles,
};
const defaultName = "Дмитрий Каргин";
const heroLabel = "AI-Portfolio — портфолио будущего";
const defaultHeadline = "ML / LLM Engineer";
const defaultDescription = "Создаю готовые AI-системы и решения для реальных сервисов.";
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
  const currentPosition = profile.current_position;

  // Separate skill tags from link tags (those with icons)
  const skillTags = heroTags.filter((t) => !t.icon);
  const linkTags = heroTags.filter((t) => t.icon);
  const displayTags = skillTags.length > 0 ? skillTags.map((t) => t.name) : fallbackTags;

  return (
    <Section
      id="hero"
      label={heroLabel}
      title=""
      className="!mt-0 !mb-0 flex flex-col justify-center pt-0 [&>div>h2]:hidden [&>div]:mb-3 sm:[&>div]:mb-4 md:[&>div]:mb-6 [&>div>p]:normal-case"
    >
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, ease: "easeOut" }}
        className="relative mx-auto w-full max-w-5xl overflow-hidden rounded-3xl border border-[#00ffc3]/25 bg-gradient-to-br from-bg-panel/80 via-black/60 to-bg-panel/80 p-5 shadow-[0_0_22px_rgba(0,255,200,0.22)] backdrop-blur sm:p-7 md:p-10 lg:p-12"
      >
        <div className="pointer-events-none absolute inset-0 opacity-70">
          <div className="absolute inset-0 animate-[glowDrift_22s_ease-in-out_infinite] bg-[radial-gradient(circle_at_30%_30%,rgba(0,255,195,0.12),transparent_35%)]" />
          <div className="absolute inset-0 animate-[gridShift_28s_linear_infinite] bg-[linear-gradient(90deg,rgba(0,255,195,0.08)_1px,transparent_1px),linear-gradient(0deg,rgba(0,255,195,0.08)_1px,transparent_1px)] bg-[size:40px_40px] opacity-30" />
          <div className="absolute inset-0 animate-[glowDrift_18s_ease-in-out_infinite] bg-[radial-gradient(circle_at_70%_60%,rgba(139,92,246,0.18),transparent_45%)]" />
        </div>
        <div className="relative flex flex-col gap-6 sm:gap-7 md:gap-8 lg:flex-row lg:items-center lg:gap-10">
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, ease: "easeOut", delay: 0.1 }}
            className="space-y-3 sm:space-y-4 md:space-y-5"
          >
            <p className="flex items-center gap-2 font-mono text-base text-accent-soft sm:text-lg">
              <span className="inline-flex items-center rounded-full border border-[#19f0c3]/60 bg-[#19f0c3]/10 px-3 py-1 text-xs font-semibold text-[#19f0c3] sm:text-sm">
                {headline}
              </span>
            </p>
            <h1 className="text-3xl font-bold leading-tight text-slate-50 sm:text-4xl lg:text-5xl xl:text-6xl">
              {displayName}
            </h1>
            <p className="max-w-2xl text-left text-base leading-relaxed text-slate-100 sm:text-lg md:max-w-3xl">
              {description}
            </p>
            {currentPosition && (
              <p className="text-sm font-mono text-accent-soft/80 sm:text-base">
                Сейчас: {currentPosition}
              </p>
            )}
            <div className="flex max-w-2xl flex-wrap gap-2 text-sm font-medium text-gray-200 sm:gap-2.5">
              {displayTags.map((tag) => (
                <span
                  key={tag}
                  className="rounded-full border border-accent/30 bg-white/5 px-3 py-1 leading-tight"
                >
                  {tag}
                </span>
              ))}
            </div>
            <div className="flex flex-wrap gap-2.5 sm:gap-3.5">
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
            <div className="relative h-48 w-48 overflow-hidden rounded-3xl border border-[#00ffc3]/40 bg-gradient-to-br from-accent/15 via-accent-alt/10 to-transparent shadow-[0_0_35px_rgba(0,255,200,0.3)] sm:h-52 sm:w-52 md:h-60 md:w-60 lg:h-72 lg:w-72">
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
