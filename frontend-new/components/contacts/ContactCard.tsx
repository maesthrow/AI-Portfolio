import { Contact } from "@/lib/types";

type ContactCardProps = {
  contact: Contact;
};

const iconMap: Record<Contact["kind"], string> = {
  email: "@",
  telegram: "TG",
  github: "GH",
  linkedin: "IN",
  other: "*"
};

export default function ContactCard({ contact }: ContactCardProps) {
  return (
    <a
      href={contact.url}
      target="_blank"
      rel="noreferrer"
      className="group flex items-center gap-3 rounded-2xl border border-[#00ffc3]/25 bg-black/40 px-4 py-3 text-sm text-slate-100 shadow-[0_0_12px_rgba(0,255,200,0.14)] transition duration-300 hover:border-[#00ffc3]/60 hover:shadow-[0_0_30px_rgba(0,255,200,0.32)]"
    >
      <div className="flex h-12 w-12 items-center justify-center rounded-xl border border-[#00ffc3]/35 bg-black/60 text-lg shadow-[0_0_10px_rgba(0,255,200,0.2)]">
        {iconMap[contact.kind] ?? "*"}
      </div>
      <div>
        <p className="font-semibold">{contact.label}</p>
        <p className="text-xs text-gray-300">{contact.value}</p>
      </div>
    </a>
  );
}
