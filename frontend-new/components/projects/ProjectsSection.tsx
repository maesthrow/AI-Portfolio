import Section from "@/components/layout/Section";
import ProjectCard from "@/components/projects/ProjectCard";
import { Project } from "@/lib/types";

type ProjectsSectionProps = {
  projects: Project[];
};

export default function ProjectsSection({ projects }: ProjectsSectionProps) {
  if (!projects?.length) return null;

  return (
    <Section
      id="projects"
      label="ИЗБРАННЫЕ ПРОЕКТЫ"
      title="Избранные проекты"
      subtitle="RAG-системы, CV-приложения, backend API и продуктовые ML-фичи."
    >
      <div className="grid gap-8 md:grid-cols-2 xl:grid-cols-3">
        {projects.map((project) => (
          <ProjectCard key={project.id} project={project} />
        ))}
      </div>
    </Section>
  );
}
