import type { ComponentType, SVGProps } from "react";

export type SocialBadgeProps = {
  href: string;
  label: string;
  icon: ComponentType<SVGProps<SVGSVGElement>>;
};

export function SocialBadge({ href, label, icon: Icon }: SocialBadgeProps) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      className="group inline-flex items-center gap-2 rounded-full border border-[#00ffc3]/50 bg-black/40 px-4 py-2 text-xs font-semibold text-accent-soft shadow-[0_0_15px_rgba(0,255,200,0.18)] transition duration-200 hover:-translate-y-1 hover:border-[#00ffc3]/70 hover:shadow-[0_0_45px_rgba(0,255,200,0.35)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/50 sm:px-5 sm:py-2.5 sm:text-sm"
    >
      <Icon className="h-4 w-4 text-current" aria-hidden="true" />
      <span>{label}</span>
    </a>
  );
}
