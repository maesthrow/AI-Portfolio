import Section from "@/components/layout/Section";
import ProjectCard from "@/components/projects/ProjectCard";
import { Project } from "@/lib/types";

type ProjectsSectionProps = {
  projects: Project[];
};

export default function ProjectsSection({ projects }: ProjectsSectionProps) {
  return (
    <Section
      id="projects"
      title="ИЗБРАННЫЕ ПРОЕКТЫ"
      subtitle="RAG-сервисы, CV-продукты, backend-API и инструменты."
    >
      <div className="grid gap-5 md:grid-cols-2">
        {projects.map((project) => (
          <ProjectCard key={project.id} project={project} />
        ))}
      </div>
    </Section>
  );
}
