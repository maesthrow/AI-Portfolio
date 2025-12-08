import { memo } from "react";

type TechTagVariant = "default" | "domain" | "highlighted" | "stack";

interface TechTagProps {
  children: React.ReactNode;
  variant?: TechTagVariant;
  domainTone?: string;
}

function TechTag({ children, variant = "default", domainTone }: TechTagProps) {
  const baseClasses =
    "px-3 py-1 rounded-full text-[11px] transition-all duration-300 cursor-default";

  if (variant === "domain" && domainTone) {
    return (
      <span
        className={`${baseClasses} border font-semibold uppercase tracking-wide shadow-[0_0_12px_rgba(0,255,200,0.25)] ${domainTone}`}
      >
        {children}
      </span>
    );
  }

  if (variant === "highlighted") {
    return (
      <span
        className={`${baseClasses} border border-[#00ffc3]/50 text-[#00ffc3] bg-[#00ffc3]/10 shadow-[0_0_10px_rgba(0,255,200,0.3)]`}
      >
        {children}
      </span>
    );
  }

  if (variant === "stack") {
    return (
      <span
        className={`${baseClasses} border border-[#00ffc3]/40 bg-[#00ffc3]/10 text-slate-100 shadow-[0_0_8px_rgba(0,255,200,0.25)] hover:border-[#00ffc3]/60 hover:text-[#00ffc3] hover:shadow-[0_0_12px_rgba(0,255,200,0.35)]`}
      >
        {children}
      </span>
    );
  }

  // default variant with hover
  return (
    <span
      className={`${baseClasses} border border-[#00ffc3]/30 bg-black/60 text-slate-200 shadow-[0_0_8px_rgba(0,255,200,0.2)] hover:border-[#00ffc3]/60 hover:text-[#00ffc3] hover:shadow-[0_0_12px_rgba(0,255,200,0.35)]`}
    >
      {children}
    </span>
  );
}

export default memo(TechTag);
