import Shell from "@/components/layout/Shell";
import HeroIntro from "@/components/hero/HeroIntro";
import HeroScrollHint from "@/components/hero/HeroScrollHint";
import { ParticlesBackground } from "@/components/hero/ParticlesBackground";
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
      <section className="relative isolate flex min-h-[calc(var(--app-dvh)-3rem)] flex-col pb-24 sm:min-h-[calc(var(--app-dvh)-4.5rem)] sm:pb-14">
        <div className="pointer-events-none absolute -z-10 inset-x-0 top-0 h-[calc(100%+12rem)] overflow-hidden sm:h-[calc(100%+16rem)]">
          <div className="hero-grid absolute inset-0 opacity-[0.16]" />
          <div className="hero-glow absolute -inset-x-24 top-[-25%] h-[140%]" />
          <ParticlesBackground />
        </div>

        <div className="flex flex-1 items-start pt-3 sm:items-center sm:pt-0">
          <div className="mx-auto w-full max-w-6xl px-4 md:px-8 lg:px-12">
            <HeroIntro profile={profile} contacts={contacts} heroTags={heroTags} />
          </div>
        </div>

        <HeroScrollHint targetId="about" />
      </section>

      {/* Timeline wrapper - линия начинается после Hero */}
      <div className="relative before:pointer-events-none before:absolute before:-left-8 before:top-0 before:h-full before:w-px before:bg-gradient-to-b before:from-accent-soft/70 before:via-accent/25 before:to-transparent">
        <AboutMeSection profile={profile} stats={stats} focusAreas={focusAreas} />
        <ExperienceSection items={experience} sectionMeta={sectionMetaMap["experience"]} />
        <ProjectsSection projects={featuredProjects} sectionMeta={sectionMetaMap["projects"]} />
        <HowIWorkSection workApproaches={workApproaches} sectionMeta={sectionMetaMap["how_i_work"]} />
        <TechFocusSection items={techFocus} sectionMeta={sectionMetaMap["tech_focus"]} />
        <PublicationsSection items={publications} sectionMeta={sectionMetaMap["publications"]} />
        <ContactsSection contacts={contacts} sectionMeta={sectionMetaMap["contacts"]} />
        <Footer />
      </div>
    </Shell>
  );
}
