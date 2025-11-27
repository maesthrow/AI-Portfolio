import type { Metadata } from "next";
import "./globals.css";
import AgentDock from "@/components/agent/AgentDock";

export const metadata: Metadata = {
  title: "AI-Portfolio — Дмитрий Каргин",
  description: "Киберпанк-портфолио с данными из content-api и AI-агентом."
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru">
      <body className="relative bg-bg-base text-slate-100">
        {children}
        <AgentDock />
      </body>
    </html>
  );
}
