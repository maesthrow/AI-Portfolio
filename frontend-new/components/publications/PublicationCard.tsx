import { Publication } from "@/lib/types";

type PublicationCardProps = {
  publication: Publication;
};

export default function PublicationCard({ publication }: PublicationCardProps) {
  return (
    <div className="group rounded-3xl border border-[#00ffc3]/20 bg-black/40 p-7 shadow-[0_0_15px_rgba(0,255,200,0.12)] transition duration-300 hover:border-[#00ffc3]/60 hover:shadow-[0_0_45px_rgba(0,255,200,0.3)]">
      <div className="flex items-center justify-between gap-2">
        <span className="rounded-full border border-[#00ffc3]/40 bg-accent/10 px-3 py-1 text-xs font-semibold text-accent shadow-[0_0_10px_rgba(0,255,200,0.25)]">
          {publication.source}
        </span>
        <span className="text-xs text-slate-400">{publication.year}</span>
      </div>
      <p className="mt-3 text-lg font-semibold text-slate-50">{publication.title}</p>
      {publication.badge ? (
        <p className="mt-1 text-xs text-accent-soft">#{publication.badge}</p>
      ) : null}
      <a
        href={publication.url}
        className="mt-4 inline-flex items-center gap-2 text-sm font-semibold text-accent hover:text-accent-soft"
        target="_blank"
        rel="noreferrer"
      >
        Читать
      </a>
    </div>
  );
}
