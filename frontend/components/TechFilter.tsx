"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

type Tech = { id: number; name: string };

export default function TechFilter({
  all,
  selected,
}: {
  all: Tech[];
  selected: number[];
}) {
  const router = useRouter();
  const sp = useSearchParams();
  const [picked, setPicked] = useState<number[]>(selected);

  useEffect(() => setPicked(selected), [selected]);

  const toggle = (id: number) => {
    const next = picked.includes(id)
      ? picked.filter((x) => x !== id)
      : [...picked, id];

    setPicked(next);

    const params = new URLSearchParams(sp.toString());
    if (next.length) params.set("tech", next.join(","));
    else params.delete("tech");

    router.replace(`/?${params.toString()}`);
  };

  return (
    <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
      {all.map((t) => (
        <button
          key={t.id}
          onClick={() => toggle(t.id)}
          className={`badge ${picked.includes(t.id) ? "" : "ghost"}`}
          style={{ cursor: "pointer" }}
          aria-pressed={picked.includes(t.id)}
        >
          {t.name}
        </button>
      ))}
      {!!picked.length && (
        <button
          onClick={() => {
            setPicked([]);
            const params = new URLSearchParams(sp.toString());
            params.delete("tech");
            router.replace(`/?${params.toString()}`);
          }}
          className="badge danger"
          style={{ marginLeft: 4, cursor: "pointer" }}
        >
          Сброс
        </button>
      )}
    </div>
  );
}
