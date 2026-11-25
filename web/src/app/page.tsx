import { PageHeader } from "@/components/ui";
import { HomeView } from "./home-view";

export default function Home() {
  return (
    <>
      <PageHeader eyebrow="PlaceIQ / Home" title="Your placement readiness">
        Where you stand, the change that would help most, and what to learn next.
      </PageHeader>
      <HomeView />
    </>
  );
}
