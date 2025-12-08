export default function Footer() {
  return (
    <footer className="group/footer relative mt-24 py-10">
      {/* Top gradient line */}
      <div className="absolute top-0 left-1/4 right-1/4 h-px bg-gradient-to-r from-transparent via-[#00ffc3]/40 to-transparent transition-all duration-300 group-hover/footer:via-[#00ffc3]/60 group-hover/footer:shadow-[0_0_12px_rgba(0,255,195,0.3)]" />

      {/* Content */}
      <div className="flex items-center justify-center gap-4">
        {/* Left decorative line */}
        <div className="hidden sm:block w-16 h-px bg-gradient-to-r from-transparent to-[#00ffc3]/40 transition-all duration-300 group-hover/footer:to-[#00ffc3]/70 group-hover/footer:shadow-[0_0_10px_rgba(0,255,195,0.3)]" />

        {/* Text with hover */}
        <p className="max-w-2xl px-4 text-center text-[#00ffc3]/75 text-sm transition-all duration-500 hover:text-[#00ffc3]/95 hover:drop-shadow-[0_0_12px_rgba(0,255,200,0.35)] cursor-default">
          <span className="text-[#00ffc3]/85">&gt;</span> Создано с использованием AI и киберпанк-эстетики | 2025
        </p>

        {/* Right decorative line */}
        <div className="hidden sm:block w-16 h-px bg-gradient-to-l from-transparent to-[#00ffc3]/40 transition-all duration-300 group-hover/footer:to-[#00ffc3]/70 group-hover/footer:shadow-[0_0_10px_rgba(0,255,195,0.3)]" />
      </div>
    </footer>
  );
}
