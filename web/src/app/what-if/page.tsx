import { PageHeader } from "@/components/ui";
import { WhatIfView } from "./what-if-view";

export const metadata = { title: "What-if simulator" };

export default function WhatIf() {
  return (
    <>
      <PageHeader eyebrow="Student / What-if" title="What if…?">
        Move the sliders to see how your estimate would change. Every number is recalculated by the trained model.
      </PageHeader>
      <WhatIfView />
    </>
  );
}
