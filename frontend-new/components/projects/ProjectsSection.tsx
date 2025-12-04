import Section from "@/components/layout/Section";
import ProjectCard from "@/components/projects/ProjectCard";
import { Project, SectionMeta } from "@/lib/types";

type ProjectsSectionProps = {
  projects: Project[];
  sectionMeta?: SectionMeta;
};

const defaultLabel = "ИЗБРАННЫЕ ПРОЕКТЫ";
const defaultTitle = "Избранные проекты";
const defaultSubtitle = "RAG-системы, CV-приложения, backend API и продуктовые ML-фичи.";

export default function ProjectsSection({ projects, sectionMeta }: ProjectsSectionProps) {
  if (!projects?.length) return null;

  return (
    <Section
      id="projects"
      label={defaultLabel}
      title={sectionMeta?.title || defaultTitle}
      subtitle={sectionMeta?.subtitle || defaultSubtitle}
    >
      <div className="grid gap-8 md:grid-cols-2 xl:grid-cols-3">
        {projects.map((project) => (
          <ProjectCard key={project.id} project={project} />
        ))}
      </div>
    </Section>
  );
}
