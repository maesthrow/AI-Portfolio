"use client";

import { useRouter } from "next/navigation";

type Project = {
  id: number;
  name: string;
  description?: string | null;
  period?: string | null;
  technologies?: string[];
  company_name?: string | null;
  company_website?: string | null;

  // новые поля
  kind?: "commercial" | "personal" | string;
  repo_url?: string | null;
  demo_url?: string | null;
};

export default function ProjectCard({ project: p }: { project: Project }) {
  const router = useRouter();
  const goto = () => router.push(`/projects/${p.id}`);
  const onKey = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      goto();
    }
  };

  const isPersonal = (p.kind ?? "commercial") === "personal";

  return (
    <div
      role="link"
      tabIndex={0}
      onClick={goto}
      onKeyDown={onKey}
      className="card"
      style={{
        display: "block",
        border: "1px solid #1f2430",
        borderRadius: 12,
        padding: 14,
        background: "#0f131a",
        textDecoration: "none",
        cursor: "pointer",
      }}
      aria-label={`Открыть проект ${p.name}`}
    >
      <header
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "baseline",
          gap: 12,
          flexWrap: "wrap",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 8, minWidth: 0 }}>
          <div
            className="project-title"
            style={{
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            {p.name}
          </div>

          {/* Бейдж компании или «Личный проект» */}
          {isPersonal ? (
            <span className="chip-alt" onClick={(e) => e.stopPropagation()}>
              Личный проект
            </span>
          ) : (
            p.company_name &&
              (p.company_website ? (
                <a
                  href={p.company_website}
                  target="_blank"
                  rel="noreferrer noopener"
                  className="badge company"
                  title={p.company_name}
                  onClick={(e) => e.stopPropagation()}
                >
                  {p.company_name}
                </a>
              ) : (
                <span
                  className="badge company"
                  title={p.company_name}
                  onClick={(e) => e.stopPropagation()}
                >
                  {p.company_name}
                </span>
              ))
          )}
        </div>

        {/* Период: у личных может не быть — просто не показываем, если пусто */}
        <div className="hint mono">{p.period || ""}</div>
      </header>

      {p.description && <p className="project-description">{p.description}</p>}

      {p.technologies?.length ? (
        <div style={{ marginTop: 8, display: "flex", gap: 6, flexWrap: "wrap" }}>
          {p.technologies.map((t) => (
            <span key={t} className="badge" onClick={(e) => e.stopPropagation()}>
              {t}
            </span>
          ))}
        </div>
      ) : null}

      {(p.repo_url || p.demo_url) && (
        <div className="links" onClick={(e) => e.stopPropagation()}>
          {p.repo_url && (
            <a href={p.repo_url} target="_blank" rel="noreferrer">
              GitHub
            </a>
          )}
          {p.repo_url && p.demo_url && <span className="dot">•</span>}
          {p.demo_url && (
            <a href={p.demo_url} target="_blank" rel="noreferrer">
              Demo
            </a>
          )}
        </div>
      )}
    </div>
  );
}
