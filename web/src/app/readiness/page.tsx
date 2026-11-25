import { PageHeader } from "@/components/ui";
import { ReadinessView } from "./readiness-view";

export const metadata = { title: "Readiness report" };

export default function Readiness() {
  return (
    <>
      <PageHeader eyebrow="Student / Readiness report" title="Your readiness report">
        Your estimated chance of campus placement, what drives it, and what to work on.
      </PageHeader>
      <ReadinessView />
    </>
  );
}
