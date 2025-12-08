export default function Footer() {
  return (
    <footer className="relative mt-24 py-10">
      {/* Top gradient line */}
      <div className="absolute top-0 left-1/4 right-1/4 h-px bg-gradient-to-r from-transparent via-[#00ffc3]/25 to-transparent" />

      {/* Content */}
      <div className="flex items-center justify-center gap-4">
        {/* Left decorative line */}
        <div className="hidden sm:block w-16 h-px bg-gradient-to-r from-transparent to-[#00ffc3]/20" />

        {/* Text with hover */}
        <p className="max-w-2xl px-4 text-center text-[#00ffc3]/65 text-sm transition-all duration-500 hover:text-[#00ffc3]/80 hover:drop-shadow-[0_0_8px_rgba(0,255,200,0.3)] cursor-default">
          <span className="text-[#00ffc3]/75">&gt;</span> Создано с использованием AI и киберпанк-эстетики | 2025
        </p>

        {/* Right decorative line */}
        <div className="hidden sm:block w-16 h-px bg-gradient-to-l from-transparent to-[#00ffc3]/20" />
      </div>
    </footer>
  );
}
