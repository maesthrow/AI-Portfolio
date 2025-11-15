"use client";

import { useState } from "react";
import Image from "next/image";

type Props = {
  src?: string;          // "/avatar.webp"
  initials?: string;     // "DK"
};

export default function Avatar({ src = "/ava.webp", initials = "DK" }: Props) {
  const [err, setErr] = useState(false);

  // Фолбэк на инициалы
  if (err) {
    return (
      <div
        style={{
          width: 44,
          height: 44,
          borderRadius: 9999,
          display: "grid",
          placeItems: "center",
          fontSize: 12,
          fontWeight: 600,
          background: "rgba(255,255,255,0.06)",
          border: "1px solid rgba(255,255,255,0.12)",
          color: "rgba(255,255,255,0.9)",
        }}
      >
        {initials}
      </div>
    );
  }

  // Круглый контейнер фиксированного размера (важно: position:relative)
  return (
    <div
      style={{
        position: "relative",
        width: 44,
        height: 44,
        borderRadius: 9999,
        overflow: "hidden",
        border: "1px solid rgba(255,255,255,0.12)",
      }}
    >
      <Image
        src={src}
        alt="Dmitriy Kargin"
        fill
        sizes="44px"
        priority
        onError={() => setErr(true)}
        placeholder="blur"
        blurDataURL="data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDQiIGhlaWdodD0iNDQiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyIvPg=="
        style={{ objectFit: "cover" }}
      />
    </div>
  );
}
