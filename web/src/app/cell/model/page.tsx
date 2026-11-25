import { CellPage } from "@/components/cell/cell-page";
import { PageHeader } from "@/components/ui";

export const metadata = { title: "Model" };

export default function Page() {
  return (
    <>
      <PageHeader eyebrow="Placement cell / Model" title="Placement model">
        Train on recorded placement outcomes and deploy. Logistic regression is the explainable default; random forest tests for non-linear gains.
      </PageHeader>
      <CellPage kind="model" />
    </>
  );
}
