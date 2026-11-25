import { CellPage } from "@/components/cell/cell-page";
import { PageHeader } from "@/components/ui";

export const metadata = { title: "Annotate resumes" };

export default function Page() {
  return (
    <>
      <PageHeader eyebrow="Placement cell / Annotate" title="Annotate resumes">
        Build the ground-truth set for the extraction study: label the skills each resume actually contains.
      </PageHeader>
      <CellPage kind="annotate" />
    </>
  );
}
