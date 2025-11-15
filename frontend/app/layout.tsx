// frontend/app/layout.tsx
import type { Metadata } from "next";
import "./globals.css";
import ChatDock from "@/components/ChatDock";

export const metadata: Metadata = {
  title: "AI-Portfolio",
  description: "Dmitriy Kargin — AI-portfolio with RAG agent",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru">
      <body style={{ background: "#0b0d10", color: "#e5e7eb", fontFamily: "ui-sans-serif, system-ui" }}>
        {children}
        {/* Глобальный чат: живет один раз на всём сайте и не размонтируется */}
        <ChatDock />
      </body>
    </html>
  );
}
