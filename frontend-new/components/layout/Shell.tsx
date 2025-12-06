type ShellProps = {
  children: React.ReactNode;
};

export default function Shell({ children }: ShellProps) {
  return (
    <div className="relative z-10 min-h-screen bg-bg-base text-slate-100">
      <div className="mx-auto max-w-5xl px-4 pb-24 pt-12 sm:px-6 sm:pt-16 lg:px-8 lg:max-w-6xl">
        {children}
      </div>
    </div>
  );
}
