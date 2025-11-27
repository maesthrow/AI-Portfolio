import { Publication } from "@/lib/types";

type PublicationCardProps = {
  publication: Publication;
};

export default function PublicationCard({ publication }: PublicationCardProps) {
  return (
    <div className="rounded-2xl border border-slate-700/60 bg-black/40 p-4 transition-transform duration-200 hover:-translate-y-1 hover:shadow-neon">
      <div className="flex items-center justify-between gap-2">
        <span className="rounded-full bg-accent/10 px-3 py-1 text-xs font-semibold text-accent">
          {publication.source}
        </span>
        <span className="text-xs text-slate-400">{publication.year}</span>
      </div>
      <p className="mt-3 text-base font-semibold text-slate-50">{publication.title}</p>
      {publication.badge ? (
        <p className="mt-1 text-xs text-accent-soft">#{publication.badge}</p>
      ) : null}
      <a
        href={publication.url}
        className="mt-3 inline-flex items-center gap-2 text-sm text-accent hover:text-accent-soft"
        target="_blank"
        rel="noreferrer"
      >
        Читать →
      </a>
    </div>
  );
}
