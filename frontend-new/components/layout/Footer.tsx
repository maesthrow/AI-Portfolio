export default function Footer() {
  return (
    <footer className="group/footer relative mt-24 py-10">
      {/* Top gradient line with dual sweep from center */}
      <div className="absolute top-0 left-1/4 right-1/4 h-px overflow-hidden transition-shadow duration-300 group-hover/footer:shadow-[0_0_12px_rgba(0,255,195,0.3)]">
        <div className="absolute inset-0 bg-gradient-to-r from-transparent via-[#00ffc3]/50 to-transparent transition-opacity duration-300 group-hover/footer:via-[#00ffc3]/60" />
        <div className="footer-top-sweep-right absolute inset-0" />
        <div className="footer-top-sweep-left absolute inset-0" />
      </div>

      {/* Content */}
      <div className="flex items-center justify-center gap-4">
        {/* Left decorative line — sweep goes inward (left → right, toward text) */}
        <div className="hidden sm:block w-16 h-px overflow-hidden relative transition-shadow duration-300 group-hover/footer:shadow-[0_0_10px_rgba(0,255,195,0.3)]">
          <div className="absolute inset-0 bg-gradient-to-r from-transparent to-[#00ffc3]/50 transition-opacity duration-300 group-hover/footer:to-[#00ffc3]/70" />
          <div className="footer-side-sweep-inward absolute inset-0" />
        </div>

        {/* Text with hover */}
        <p className="max-w-2xl px-4 text-center text-[#00ffc3]/80 text-sm transition-all duration-500 hover:text-[#00ffc3]/95 hover:drop-shadow-[0_0_12px_rgba(0,255,200,0.35)] cursor-default">
          <span className="text-[#00ffc3]/90">&gt;</span> Создано с использованием AI и киберпанк-эстетики | 2026
        </p>

        {/* Right decorative line — sweep goes inward (right → left, toward text) */}
        <div className="hidden sm:block w-16 h-px overflow-hidden relative transition-shadow duration-300 group-hover/footer:shadow-[0_0_10px_rgba(0,255,195,0.3)]">
          <div className="absolute inset-0 bg-gradient-to-l from-transparent to-[#00ffc3]/50 transition-opacity duration-300 group-hover/footer:to-[#00ffc3]/70" />
          <div className="footer-side-sweep-inward-reverse absolute inset-0" />
        </div>
      </div>
    </footer>
  );
}
