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
      title="СВЯЗАТЬСЯ СО МНОЙ"
      subtitle="root@portfolio ~ $ contact --list"
    >
      <div className="rounded-3xl border border-accent/30 bg-bg-panel/80 p-6 shadow-neon">
        <p className="font-mono text-xs text-accent-soft">
          Инициализация модуля связи… <span className="text-accent">✓</span> Контакты загружены.
        </p>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          {contacts.map((contact) => (
            <ContactCard key={`${contact.kind}-${contact.value}`} contact={contact} />
          ))}
        </div>
        <div className="mt-5 flex items-center gap-2 font-mono text-sm text-accent-soft">
          &gt; status: <span className="animate-pulse text-accent">open_to_opportunities_</span>
        </div>
      </div>
    </Section>
  );
}
