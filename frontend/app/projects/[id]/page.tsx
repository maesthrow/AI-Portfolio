import BackButton from "@/components/BackButton";
import { getProject } from "@/lib/api";

type ProjectDetail = {
  id: number;
  name: string;
  description?: string | null;
  period?: string | null;
  technologies?: string[];
  company_name?: string | null;
  company_website?: string | null;

  // новые поля (безопасно опциональные)
  kind?: "commercial" | "personal" | string;
  repo_url?: string | null;
  demo_url?: string | null;

  achievements?: { title: string; description?: string | null; links?: string[] }[];
  documents?: { title: string; url: string; doc_type?: string | null }[];
};

type Props = { params: { id: string } };

export default async function ProjectPage({ params }: Props) {
  const p: ProjectDetail = await getProject(params.id);

  // ✅ НОРМАЛИЗУЕМ kind, т.к. с бэка может прийти "PERSONAL"/"COMMERCIAL"
  const kind = (p.kind ?? "").toString().toLowerCase();
  const isPersonal = kind === "personal";

  return (
    <main className="container">
      <div style={{ marginBottom: 12 }}>
        <BackButton fallbackHref="/" />
      </div>

      <article className="card" style={{ paddingBottom: 16 }}>
        <header
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "baseline",
            gap: 12,
            marginBottom: 6,
            flexWrap: "wrap",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 10, minWidth: 0 }}>
            <h1 style={{ margin: 0, fontSize: 28, fontWeight: 800, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {p.name}
            </h1>

            {/* Бейдж компании или «Личный проект» */}
            {isPersonal ? (
              <span className="chip-alt">Личный проект</span>
            ) : (
              p.company_name &&
                (p.company_website ? (
                  <a
                    href={p.company_website}
                    target="_blank"
                    rel="noreferrer noopener"
                    className="badge company"
                    title={p.company_name}
                  >
                    {p.company_name}
                  </a>
                ) : (
                  <span className="badge company" title={p.company_name}>
                    {p.company_name}
                  </span>
                ))
            )}
          </div>

          {/* Период показываем, если он есть (для личных может отсутствовать — это ок) */}
          {p.period && <div className="hint mono">{p.period}</div>}
        </header>

        {p.description && <p className="project-description">{p.description}</p>}

        {/* Опциональные ссылки на исходники/демо */}
        {(p.repo_url || p.demo_url) && (
          <div className="links" style={{ marginTop: 6 }}>
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

        {p.technologies?.length ? (
          <div style={{ marginTop: 12, display: "flex", gap: 8, flexWrap: "wrap" }}>
            {p.technologies.map((t) => (
              <span key={t} className="badge">
                {t}
              </span>
            ))}
          </div>
        ) : null}

        {p.achievements?.length ? (
          <>
            <hr />
            <section>
              <h3 style={{ marginTop: 0 }}>Достижения</h3>
              <div style={{ display: "grid", gap: 12 }}>
                {p.achievements.map((a, idx) => (
                  <div key={idx} className="card" style={{ padding: 12 }}>
                    <div style={{ fontWeight: 700, marginBottom: 6 }}>{a.title}</div>
                    {a.description && (
                      <div className="hint" style={{ marginBottom: 8 }}>
                        {a.description}
                      </div>
                    )}
                    {a.links?.length ? (
                      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                        {a.links.map((url, i) => (
                          <a
                            key={i}
                            href={url}
                            target="_blank"
                            rel="noreferrer noopener"
                            className="badge ghost"
                            title={url}
                          >
                            Ссылка {i + 1}
                          </a>
                        ))}
                      </div>
                    ) : null}
                  </div>
                ))}
              </div>
            </section>
          </>
        ) : null}

        {p.documents?.length ? (
          <>
            <hr />
            <section>
              <h3 style={{ marginTop: 0 }}>Документы</h3>
              <div style={{ display: "grid", gap: 10 }}>
                {p.documents.map((d, idx) => (
                  <div
                    key={idx}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      gap: 12,
                      border: "1px solid #1f2430",
                      borderRadius: 12,
                      padding: "10px 12px",
                      background: "#0f131a",
                    }}
                  >
                    <div>
                      <a
                        href={d.url}
                        target="_blank"
                        rel="noreferrer noopener"
                        style={{ color: "#e2ecf7", textDecoration: "none" }}
                        title={d.url}
                      >
                        {d.title}
                      </a>
                      {d.doc_type && (
                        <span className="badge ghost" style={{ marginLeft: 8 }}>
                          {d.doc_type}
                        </span>
                      )}
                    </div>
                    <a
                      className="badge"
                      href={d.url}
                      target="_blank"
                      rel="noreferrer noopener"
                      title="Открыть"
                    >
                      Открыть
                    </a>
                  </div>
                ))}
              </div>
            </section>
          </>
        ) : null}
      </article>
    </main>
  );
}
