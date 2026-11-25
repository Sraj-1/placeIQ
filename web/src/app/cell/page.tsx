import { CellPage } from "@/components/cell/cell-page";
import { PageHeader } from "@/components/ui";

export const metadata = { title: "Batch dashboard" };

export default function Page() {
  return (
    <>
      <PageHeader eyebrow="Placement cell / Dashboard" title="Batch readiness">
        Readiness of profiles students chose to share, scored by the current model, with training groups to plan sessions.
      </PageHeader>
      <CellPage kind="dashboard" />
    </>
  );
}
