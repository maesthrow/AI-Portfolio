import { Contact } from "@/lib/types";

type ContactCardProps = {
  contact: Contact;
};

const ContactIcons: Record<Contact["kind"] | "default", JSX.Element> = {
  email: (
    <svg
      viewBox="0 0 24 24"
      className="h-6 w-6"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.6}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <rect x="3" y="5" width="18" height="14" rx="2.2" ry="2.2" />
      <path d="M3.5 7.5 12 13.2 20.5 7.5" />
    </svg>
  ),
  telegram: (
    <svg viewBox="0 0 24 24" className="h-6 w-6" fill="currentColor">
      <path d="M21.5 4.6a1 1 0 0 0-1-.2L3.5 11.2c-1 .4-.9 1.8.2 2l3.6.9 1 3.6c.3 1 .4 1.3 1.3 1.3.6 0 .9-.3 1.3-.7l2.2-2.2 3.4 2.5c.9.5 2 .1 2.3-.9l3-12a1 1 0 0 0-.3-1Zm-4.6 2.3-8 7.3-.4 3.5-1-3.6 9.4-7.2Z" />
    </svg>
  ),
  github: (
    <svg viewBox="0 0 24 24" className="h-6 w-6" fill="currentColor">
      <path d="M12 1.2C6 1.2 1.4 5.7 1.4 11.6c0 4.6 2.9 8.5 7 9.9.5.1.7-.2.7-.5v-2c-2.8.6-3.4-1.3-3.4-1.3-.4-.9-1-1.1-1-1.1-.8-.6.1-.6.1-.6.9.1 1.4 1 1.4 1 .8 1.4 2.2 1 2.8.8.1-.6.3-1 .6-1.3-2.3-.3-4.8-1.2-4.8-5.2 0-1.1.4-2 1-2.7-.1-.3-.4-1.3.1-2.6 0 0 .9-.3 2.8 1a10 10 0 0 1 5 0c2-1.3 2.8-1 2.8-1 .5 1.3.2 2.3.1 2.6.7.7 1 1.6 1 2.7 0 4-2.5 4.9-4.9 5.2.4.3.7 1 .7 2.2v3.2c0 .3.2.6.7.5a10.4 10.4 0 0 0 7-10c0-5.9-4.6-10.4-10.6-10.4Z" />
    </svg>
  ),
  linkedin: (
    <svg viewBox="0 0 24 24" className="h-6 w-6" fill="currentColor">
      <path d="M4.9 9.4H2.3v12.2h2.6V9.4Zm.2-3.9a1.5 1.5 0 1 0-3 0c0 .8.7 1.5 1.5 1.5.9 0 1.5-.7 1.5-1.5ZM22 21.6v-7.7c0-3-1.6-4.4-3.9-4.4-1.8 0-2.6 1-3 1.6V9.4H12c0 .7 0 12.2 0 12.2h3.1v-6.8c0-.4 0-.8.1-1 .3-.8 1-1.6 2-1.6 1.3 0 1.9 1.2 1.9 3v6.4H22Z" />
    </svg>
  ),
  default: (
    <svg
      viewBox="0 0 24 24"
      className="h-6 w-6"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.6}
      strokeLinecap="round"
    >
      <circle cx="12" cy="12" r="8" />
      <path d="M12 8v8M8 12h8" />
    </svg>
  ),
};

const ContactColors: Record<Contact["kind"] | "default", string> = {
  telegram:
    "border-sky-400/60 bg-sky-500/10 text-sky-100 shadow-[0_0_12px_rgba(56,189,248,0.25)]",
  email:
    "border-emerald-400/60 bg-emerald-500/10 text-emerald-100 shadow-[0_0_12px_rgba(52,211,153,0.25)]",
  github:
    "border-slate-500/60 bg-slate-700/30 text-slate-100 shadow-[0_0_12px_rgba(148,163,184,0.25)]",
  linkedin:
    "border-purple-400/60 bg-purple-500/10 text-purple-100 shadow-[0_0_12px_rgba(168,85,247,0.25)]",
  other:
    "border-[#00ffc3]/50 bg-accent/10 text-accent shadow-[0_0_12px_rgba(0,255,200,0.25)]",
  default:
    "border-[#00ffc3]/50 bg-accent/10 text-accent shadow-[0_0_12px_rgba(0,255,200,0.25)]",
};

export default function ContactCard({ contact }: ContactCardProps) {
  const icon = ContactIcons[contact.kind] || ContactIcons.default;
  const colorClass = ContactColors[contact.kind] || ContactColors.default;

  return (
    <a
      href={contact.url}
      target="_blank"
      rel="noreferrer"
      className="group flex items-center gap-4 rounded-2xl border border-[#00ffc3]/25
                 bg-black/50 px-5 py-4 text-sm text-slate-100
                 shadow-[0_0_12px_rgba(0,255,200,0.14)]
                 transition duration-300 hover:border-[#00ffc3]/60 hover:shadow-[0_0_30px_rgba(0,255,200,0.32)]"
    >
      <div
        className={`flex h-12 w-12 items-center justify-center rounded-xl border transition ${colorClass} group-hover:scale-[1.02]`}
      >
        {icon}
      </div>
      <div>
        <p className="font-semibold">{contact.label}</p>
        <p className="text-xs text-gray-300 group-hover:text-slate-100/90">
          {contact.value}
        </p>
      </div>
    </a>
  );
}
