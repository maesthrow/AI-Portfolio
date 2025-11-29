import Shell from "@/components/layout/Shell";
import HeroIntro from "@/components/hero/HeroIntro";
import AboutMeSection from "@/components/about/AboutMeSection";
import ExperienceSection from "@/components/experience/ExperienceSection";
import HowIWorkSection from "@/components/how/HowIWorkSection";
import TechFocusSection from "@/components/tech/TechFocusSection";
import ProjectsSection from "@/components/projects/ProjectsSection";
import PublicationsSection from "@/components/publications/PublicationsSection";
import ContactsSection from "@/components/contacts/ContactsSection";
import Footer from "@/components/layout/Footer";
import {
  getContacts,
  getExperience,
  getProfile,
  getProjects,
  getPublications,
  getStats,
  getTechFocus
} from "@/lib/api";

export default async function Page() {
  const [profile, experience, stats, techFocus, projects, publications, contacts] =
    await Promise.all([
      getProfile(),
      getExperience(),
      getStats(),
      getTechFocus(),
      getProjects(),
      getPublications().catch(() => []),
      getContacts()
    ]);

  const featuredProjects = projects.filter((p) => p.featured);

  return (
    <Shell>
      <HeroIntro profile={profile} contacts={contacts} />
      <AboutMeSection profile={profile} stats={stats} />
      <ExperienceSection items={experience} />
      <HowIWorkSection />
      <TechFocusSection items={techFocus} />
      <ProjectsSection projects={featuredProjects} />
      <PublicationsSection items={publications} />
      <ContactsSection contacts={contacts} />
      <Footer />
    </Shell>
  );
}
