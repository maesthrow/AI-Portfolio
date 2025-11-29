import Link from "next/link";
import Section from "@/components/layout/Section";
import { Contact, Profile } from "@/lib/types";

type HeroIntroProps = {
  profile: Profile;
  contacts: Contact[];
};

const primaryContacts: Contact["kind"][] = ["github", "telegram", "linkedin", "other"];

function contactLink(contacts: Contact[], kind: Contact["kind"]) {
  return contacts.find((c) => c.kind === kind);
}

export default function HeroIntro({ profile, contacts }: HeroIntroProps) {
  const avatar = (profile as any).avatarUrl ?? (profile as any).avatar_url ?? null;

  return (
    <Section
      id="hero"
      title="DMITRIY KARGIN"
      subtitle="Python / ML инженер — CV, LLM, RAG"
      className="pt-8"
    >
      <div className="relative overflow-hidden rounded-3xl border border-[#00ffc3]/25 bg-gradient-to-br from-bg-panel/80 via-black/60 to-bg-panel/80 p-14 shadow-[0_0_35px_rgba(0,255,200,0.35)] backdrop-blur">
        <div className="pointer-events-none absolute inset-0 opacity-60">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_30%,rgba(0,255,195,0.12),transparent_35%)]" />
          <div className="absolute inset-0 bg-[linear-gradient(90deg,rgba(0,255,195,0.08)_1px,transparent_1px),linear-gradient(0deg,rgba(0,255,195,0.08)_1px,transparent_1px)] bg-[size:40px_40px] opacity-30" />
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_70%_60%,rgba(139,92,246,0.15),transparent_45%)]" />
        </div>
        <div className="relative grid gap-10 sm:grid-cols-[2fr,1fr] sm:items-center">
          <div className="space-y-6">
            <p className="flex items-center gap-2 font-mono text-lg text-accent-soft">
              &gt;_ {profile.title} <span className="animate-pulse opacity-80">_</span>
            </p>
            <h1 className="text-5xl font-bold leading-tight text-slate-50 sm:text-6xl">
              {profile.name || "DMITRIY KARGIN"}
            </h1>
            <p className="max-w-2xl text-lg leading-relaxed text-gray-300">
              {profile.subtitle ||
                "ML/LLM инженер, фокус на CV и RAG-системах. Делаю надёжные AI-функции на прочном бэкенде и довожу до продакшена."}
            </p>
            <div className="flex flex-wrap gap-4">
              {primaryContacts.map((kind) => {
                const item = contactLink(contacts, kind);
                if (!item) return null;
                return (
                  <Link
                    key={kind}
                    href={item.url}
                    className="group inline-flex items-center gap-2 rounded-full border border-[#00ffc3]/50 bg-black/40 px-5 py-2.5 text-sm font-semibold text-slate-100 shadow-[0_0_25px_rgba(0,255,200,0.25)] transition-transform duration-200 hover:-translate-y-1 hover:scale-105 hover:border-[#00ffc3]/70 hover:shadow-[0_0_45px_rgba(0,255,200,0.35)]"
                    target="_blank"
                    rel="noreferrer"
                  >
                    <span className="h-2 w-2 rounded-full bg-accent-soft group-hover:animate-pulse" />
                    {item.label}
                  </Link>
                );
              })}
            </div>
          </div>
          <div className="relative flex h-full items-center justify-center">
            <div className="relative h-60 w-60 overflow-hidden rounded-3xl border border-[#00ffc3]/40 bg-gradient-to-br from-accent/15 via-accent-alt/10 to-transparent shadow-[0_0_35px_rgba(0,255,200,0.3)] sm:h-64 sm:w-64">
              {avatar ? (
                <img
                  src={avatar}
                  alt={profile.name || "avatar"}
                  className="h-full w-full object-cover"
                />
              ) : (
                <>
                  <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_20%,rgba(34,240,192,0.4),transparent_35%),radial-gradient(circle_at_70%_60%,rgba(139,92,246,0.25),transparent_40%)]" />
                  <div className="absolute inset-0 flex items-center justify-center font-mono text-xs uppercase text-accent-soft/80">
                    avatar
                  </div>
                </>
              )}
            </div>
            <div className="absolute -bottom-8 left-1/2 flex -translate-x-1/2 items-center gap-2 font-mono text-sm text-accent-soft">
              <span className="text-xl leading-none text-[#00ffc3]">{"\u2193"}</span> листай
              <span className="animate-pulse opacity-80">_</span>
            </div>
          </div>
        </div>
      </div>
    </Section>
  );
}
