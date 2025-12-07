import { Contact, ExperienceItem } from "@/lib/types";

export function normalizeTech(
  value: string | { id?: string | number; name?: string } | null | undefined
): string | null {
  if (typeof value === "string") return value;
  if (value?.name) return value.name;
  if (value?.id !== undefined) return String(value.id);
  return null;
}

export function formatPeriod(start?: string | null, end?: string | null, isCurrent?: boolean) {
  if (!start) return null;
  const startYear = new Date(start).getFullYear();
  const endYear = end ? new Date(end).getFullYear() : null;
  if (isCurrent || (!end && !endYear)) return `${startYear} — н.в.`;
  if (endYear) return `${startYear} — ${endYear}`;
  return `${startYear}`;
}

export function shortDescription(md?: string | null, maxLines = 2) {
  if (!md) return null;
  const lines = md
    .split("\n")
    .map((line) => line.replace(/^[*-]\s*/, "").trim())
    .filter(Boolean);
  if (!lines.length) return null;
  return lines.slice(0, maxLines).join(" ");
}

export function uniqueContacts(contacts: Contact[] = []) {
  const seen = new Set<string>();
  return contacts.filter((contact) => {
    const key = `${contact.kind}-${contact.value}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

export function sortExperience(items: ExperienceItem[]) {
  return [...items].sort((a, b) => {
    if (a.is_current !== b.is_current) return a.is_current ? -1 : 1;
    const aDate = a.start_date ? new Date(a.start_date).getTime() : 0;
    const bDate = b.start_date ? new Date(b.start_date).getTime() : 0;
    if (aDate !== bDate) return bDate - aDate;
    return (a.order_index ?? 0) - (b.order_index ?? 0);
  });
}
