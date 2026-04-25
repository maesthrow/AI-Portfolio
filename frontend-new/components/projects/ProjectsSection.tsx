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
      <div
        className={
          "grid gap-8 md:grid-cols-2 xl:grid-cols-3 " +
          // 2-col: center lone last when total is odd (3, 5, 7…)
          "md:[&>*:last-child:nth-child(odd)]:col-span-2 md:[&>*:last-child:nth-child(odd)]:mx-auto md:[&>*:last-child:nth-child(odd)]:w-[calc(50%-1rem)] " +
          // 3-col: reset the md rule (lone-in-2-col differs from lone-in-3-col)
          "xl:[&>*:last-child:nth-child(odd)]:col-span-1 xl:[&>*:last-child:nth-child(odd)]:mx-0 xl:[&>*:last-child:nth-child(odd)]:w-auto " +
          // 3-col: center lone last when total = 3n+1 (4, 7, 10…)
          "xl:[&>*:last-child:nth-child(3n+1)]:col-span-3 xl:[&>*:last-child:nth-child(3n+1)]:mx-auto xl:[&>*:last-child:nth-child(3n+1)]:w-[calc(33.333%-1.333rem)]"
        }
      >
        {projects.map((project) => (
          <ProjectCard key={project.id} project={project} />
        ))}
      </div>
    </Section>
  );
}
