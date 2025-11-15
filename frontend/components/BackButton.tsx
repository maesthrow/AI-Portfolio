"use client";

import { useRouter } from "next/navigation";
import Link from "next/link";

type Props = { fallbackHref?: string };

export default function BackButton({ fallbackHref = "/" }: Props) {
  const router = useRouter();

  const onClick = () => {
    // если есть history — вернёмся, иначе пойдём на fallback
    if (typeof window !== "undefined" && window.history.length > 1) {
      router.back();
    } else {
      router.push(fallbackHref);
    }
  };

  return (
    <button className="badge ghost" onClick={onClick} aria-label="Назад">
      ← Назад
    </button>
  );
}
