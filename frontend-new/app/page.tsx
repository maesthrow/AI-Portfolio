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
  getAllSectionMeta,
  getContacts,
  getExperience,
  getFeaturedProjects,
  getFocusAreas,
  getHeroTags,
  getProfile,
  getPublications,
  getStats,
  getTechFocus,
  getWorkApproaches
} from "@/lib/api";

export default async function Page() {
  const [
    profile,
    experience,
    stats,
    techFocus,
    featuredProjects,
    publications,
    contacts,
    heroTags,
    focusAreas,
    workApproaches,
    sectionMeta
  ] = await Promise.all([
    getProfile(),
    getExperience(),
    getStats(),
    getTechFocus(),
    getFeaturedProjects(),
    getPublications().catch(() => []),
    getContacts(),
    getHeroTags().catch(() => []),
    getFocusAreas().catch(() => []),
    getWorkApproaches().catch(() => []),
    getAllSectionMeta().catch(() => [])
  ]);

  const sectionMetaMap = Object.fromEntries(
    sectionMeta.map((s) => [s.section_key, s])
  );

  return (
    <Shell>
      <HeroIntro profile={profile} contacts={contacts} heroTags={heroTags} />
      <AboutMeSection profile={profile} stats={stats} focusAreas={focusAreas} />
      <ExperienceSection items={experience} sectionMeta={sectionMetaMap["experience"]} />
      <ProjectsSection projects={featuredProjects} sectionMeta={sectionMetaMap["projects"]} />
      <HowIWorkSection workApproaches={workApproaches} sectionMeta={sectionMetaMap["how_i_work"]} />
      <TechFocusSection items={techFocus} sectionMeta={sectionMetaMap["tech_focus"]} />
      <PublicationsSection items={publications} sectionMeta={sectionMetaMap["publications"]} />
      <ContactsSection contacts={contacts} sectionMeta={sectionMetaMap["contacts"]} />
      <Footer />
    </Shell>
  );
}
