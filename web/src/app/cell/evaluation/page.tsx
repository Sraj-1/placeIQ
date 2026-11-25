import { CellPage } from "@/components/cell/cell-page";
import { PageHeader } from "@/components/ui";

export const metadata = { title: "Evaluation" };

export default function Page() {
  return (
    <>
      <PageHeader eyebrow="Placement cell / Evaluation" title="Evaluation">
        Is skill extraction accurate, does similarity predict placement as well as the classifier, and is the model fair across groups?
      </PageHeader>
      <CellPage kind="evaluation" />
    </>
  );
}
