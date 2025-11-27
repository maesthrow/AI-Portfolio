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
      subtitle="Python / ML Engineer — CV, LLM, RAG"
      className="pt-6"
    >
      <div className="grid gap-8 rounded-3xl border border-accent/30 bg-bg-panel/80 p-8 shadow-neon backdrop-blur sm:grid-cols-[2fr,1fr] sm:items-center">
        <div className="space-y-4">
          <p className="font-mono text-lg text-accent-soft">&gt;_ {profile.title}</p>
          <h1 className="text-3xl font-semibold text-slate-50 sm:text-4xl">
            {profile.name || "DMITRIY KARGIN"}
          </h1>
          <p className="max-w-2xl text-base text-slate-300">
            {profile.subtitle ||
              "ML/LLM инженер, строю CV- и RAG-продукты, совмещаю экспертизу в .NET backend и ML инфраструктуре."}
          </p>
          <div className="flex flex-wrap gap-3">
            {primaryContacts.map((kind) => {
              const item = contactLink(contacts, kind);
              if (!item) return null;
              return (
                <Link
                  key={kind}
                  href={item.url}
                  className="group inline-flex items-center gap-2 rounded-full border border-accent/60 bg-black/40 px-4 py-2 text-sm font-medium text-slate-100 shadow-neon transition-all duration-200 hover:-translate-y-0.5 hover:shadow-neon-strong"
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
          <div className="relative h-40 w-40 overflow-hidden rounded-3xl border border-accent/30 bg-gradient-to-br from-accent/10 via-accent-alt/10 to-transparent shadow-neon sm:h-48 sm:w-48">
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
          <div className="absolute -bottom-6 left-1/2 -translate-x-1/2 font-mono text-xs text-accent-soft">
            ▼ scroll
          </div>
        </div>
      </div>
    </Section>
  );
}
