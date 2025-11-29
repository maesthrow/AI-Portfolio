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
      title="Избранные проекты"
      subtitle="RAG-системы, CV-пайплайны, backend API и продакшн-интеграции ML."
    >
      <div className="grid gap-8 md:grid-cols-2">
        {projects.map((project) => (
          <ProjectCard key={project.id} project={project} />
        ))}
      </div>
    </Section>
  );
}
