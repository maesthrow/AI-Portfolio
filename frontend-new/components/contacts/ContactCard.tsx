import { Contact } from "@/lib/types";

type ContactCardProps = {
  contact: Contact;
};

const iconMap: Record<Contact["kind"], string> = {
  email: "✉️",
  telegram: "💬",
  github: "☁️",
  linkedin: "🔗",
  other: "📡"
};

export default function ContactCard({ contact }: ContactCardProps) {
  return (
    <a
      href={contact.url}
      target="_blank"
      rel="noreferrer"
      className="flex items-center gap-3 rounded-2xl border border-accent/20 bg-black/40 px-4 py-3 text-sm text-slate-100 transition-all duration-200 hover:-translate-y-1 hover:border-accent/60 hover:shadow-neon"
    >
      <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-accent/30 bg-black/60 text-lg">
        {iconMap[contact.kind] ?? "📡"}
      </div>
      <div>
        <p className="font-semibold">{contact.label}</p>
        <p className="text-xs text-slate-400">{contact.value}</p>
      </div>
    </a>
  );
}
