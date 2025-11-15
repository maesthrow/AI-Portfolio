import TechFilter from "@/components/TechFilter";
import ProjectCard from "@/components/ProjectCard";
import WelcomeCard from "@/components/WelcomeCard";
import { getProjects, getTechnologies } from "@/lib/api";

type ProjectVm = {
  id: number;
  name: string;
  description?: string | null;
  period?: string | null;
  technologies?: string[];
  company_name?: string | null;
  company_website?: string | null;

  // новые поля из API
  kind?: "commercial" | "personal" | string;
  weight?: number;
  repo_url?: string | null;
  demo_url?: string | null;
};

export default async function Page({
  searchParams,
}: {
  searchParams?: { [k: string]: string };
}) {
  const selectedIds =
    (searchParams?.tech ?? "")
      .split(",")
      .map((s) => parseInt(s, 10))
      .filter((n) => Number.isFinite(n)) || [];

  const [technologies, projectsRaw] = await Promise.all([
    getTechnologies().catch(() => []),
    getProjects({ technology_id: selectedIds }).catch(() => []),
  ]);

  // Нормализуем kind, чтобы точно было "commercial"/"personal"
  const projects: ProjectVm[] = (projectsRaw as ProjectVm[]).map((p) => ({
    ...p,
    kind: (p.kind as any)?.toString().toLowerCase() as ProjectVm["kind"] ?? "commercial",
  }));

  const commercial = projects.filter((p) => (p.kind ?? "commercial") === "commercial");
  const personal   = projects.filter((p) => p.kind === "personal");

  return (
    <main className="container">
      <header style={{ marginBottom: 24 }}>
        <div className="badge mono">Dmitriy Kargin</div>
        <h1 style={{ margin: "10px 0 6px", fontSize: 32, fontWeight: 800 }}>
          AI-Portfolio
        </h1>
        <div className="hint">
          FastAPI · PostgreSQL · ChromaDB · LangChain · vLLM · LiteLLM
        </div>
      </header>

      {/* Welcome / Hero карточка */}
      <div className="mb-6">
        <WelcomeCard />
      </div>

      <section className="card" style={{ marginBottom: 12 }}>
        <h3 style={{ marginTop: 0 }}>Фильтр по технологиям</h3>
        <TechFilter all={technologies} selected={selectedIds} />
      </section>

      <section className="card">
        <h2 style={{ marginTop: 0 }}>Проекты</h2>

        {!projects?.length && (
          <div className="hint">Проектов по выбранным технологиям не найдено.</div>
        )}

        {!!commercial.length && (
          <div style={{ display: "grid", gap: 12 }}>
            {commercial.map((p) => (
              <ProjectCard key={p.id} project={p} />
            ))}
          </div>
        )}

        {!!personal.length && (
          <>
            <div className="section-sep">Личные проекты</div>
            <div style={{ display: "grid", gap: 12 }}>
              {personal.map((p) => (
                <ProjectCard key={p.id} project={p} />
              ))}
            </div>
          </>
        )}
      </section>
    </main>
  );
}