import Section from "@/components/layout/Section";
import ContactCard from "@/components/contacts/ContactCard";
import { Contact } from "@/lib/types";

type ContactsSectionProps = {
  contacts: Contact[];
};

export default function ContactsSection({ contacts }: ContactsSectionProps) {
  return (
    <Section
      id="contacts"
      label="СВЯЗАТЬСЯ СО МНОЙ"
      title="Контакты и связи"
      subtitle="Воспользуйтесь моими контактами или обратитесь за помощью к AI-агенту."
      className="mt-32"
    >
      <div className="relative overflow-hidden rounded-3xl border border-[#00ffc3]/25 bg-gradient-to-br from-bg-panel/80 via-black/60 to-bg-panel/80 p-6 shadow-[0_0_18px_rgba(0,255,200,0.16)] transition duration-300 hover:shadow-[0_0_40px_rgba(0,255,200,0.32)] sm:p-8">
        <div className="pointer-events-none absolute inset-0 opacity-40">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_25%_20%,rgba(0,255,195,0.12),transparent_35%)]" />
          <div className="absolute inset-0 bg-[linear-gradient(90deg,rgba(0,255,195,0.08)_1px,transparent_1px),linear-gradient(0deg,rgba(0,255,195,0.08)_1px,transparent_1px)] bg-[size:36px_36px] opacity-25" />
        </div>
        <div className="relative space-y-3 font-mono text-sm text-accent-soft">
          <p>
            root@portfolio ~ $ contact --list <span className="animate-pulse opacity-80">_</span>
          </p>
          <p className="text-xs text-gray-300">инициализирую модуль связи...</p>
          <p className="text-xs text-accent">✓ Загружены контакты</p>
        </div>
        <div className="relative mt-5 grid gap-6 sm:grid-cols-2">
          {contacts.map((contact) => (
            <ContactCard key={`${contact.kind}-${contact.value}`} contact={contact} />
          ))}
        </div>
        <div className="relative mt-6 flex items-center gap-2 font-mono text-sm text-accent-soft">
          &gt; status: <span className="animate-pulse opacity-80">ready_to_connect_</span>
        </div>
      </div>
    </Section>
  );
}
