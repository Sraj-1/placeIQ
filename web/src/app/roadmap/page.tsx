import { PageHeader } from "@/components/ui";
import { RoadmapView } from "./roadmap-view";

export const metadata = { title: "Roadmap" };

export default function Roadmap() {
  return (
    <>
      <PageHeader eyebrow="Student / Roadmap" title="Your roadmap">
        How your skills compare with each role&apos;s job description, and how close you are to each recruiter&apos;s eligibility criteria.
      </PageHeader>
      <RoadmapView />
    </>
  );
}
