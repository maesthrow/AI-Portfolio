import type { Metadata } from "next";
import "./globals.css";
import AgentDock from "@/components/agent/AgentDock";
import CustomCursor from "@/components/ui/CustomCursor";

export const metadata: Metadata = {
  title: "AI-Portfolio — Дмитрий Каргин",
  description: "Киберпанк-портфолио с данными из content-api и AI-агентом."
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru">
      <body className="relative overflow-x-hidden bg-bg-base text-slate-100">
        <CustomCursor />
        <div className="pointer-events-none fixed inset-0 z-0 bg-[radial-gradient(circle_at_10%_20%,rgba(0,255,195,0.08),transparent_28%),radial-gradient(circle_at_85%_10%,rgba(139,92,246,0.08),transparent_30%),radial-gradient(circle_at_50%_80%,rgba(0,255,195,0.06),transparent_35%)]" />
        <div className="relative z-10">
          {children}
          <AgentDock />
        </div>
      </body>
    </html>
  );
}
