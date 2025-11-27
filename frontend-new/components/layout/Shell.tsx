type ShellProps = {
  children: React.ReactNode;
};

export default function Shell({ children }: ShellProps) {
  return (
    <div className="min-h-screen bg-bg-base text-slate-100">
      <div className="mx-auto max-w-5xl px-4 pb-24 pt-16 sm:px-6 lg:px-8">
        <div className="relative before:pointer-events-none before:absolute before:-left-8 before:top-10 before:h-full before:w-px before:bg-gradient-to-b before:from-accent-soft/60 before:via-accent/20 before:to-transparent">
          {children}
        </div>
      </div>
    </div>
  );
}
