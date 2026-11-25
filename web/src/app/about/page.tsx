import { Card, CardTitle, PageHeader } from "@/components/ui";
import { DataSources } from "./data-sources";

export const metadata = { title: "About" };

export default function About() {
  return (
    <>
      <PageHeader eyebrow="About" title="About PlaceIQ">
        Placement readiness prediction and skill-gap analysis using machine learning and explainable AI.
      </PageHeader>

      <div className="mt-5 grid gap-5 lg:grid-cols-2">
        <Card>
          <CardTitle>The project</CardTitle>
          <p className="text-sm leading-6 text-muted">
            Minor project, B.Tech Computer Science and Engineering, Guru Tegh Bahadur Institute of Technology (GGSIPU), 2023–2027,
            by Saurabh Raj, Abu Bakar and Punit Singh.
          </p>
          <p className="mt-3 text-sm leading-6 text-muted">
            PlaceIQ estimates a student's chance of campus placement with a model trained on recorded placement outcomes (who was and wasn't placed),
            explains each estimate with SHAP, and turns it into ranked, actionable guidance. The placement cell sees batch
            readiness and training groups, and can test whether resume–JD similarity predicts placement as well as the classifier does.
          </p>
        </Card>
        <Card>
          <CardTitle>Principles</CardTitle>
          <ul className="list-disc space-y-2 pl-5 text-sm leading-6 text-muted">
            <li>Outcome-grounded: trained on whether students were placed, not on how similar a CV is to a job description. The current model uses public datasets until your college&apos;s own records are available.</li>
            <li>No invented numbers: every figure on screen is computed by the model.</li>
            <li>Private by default: runs on this computer; CVs are never stored; sharing is consent-based and anonymised.</li>
            <li>Fairness is audited, not assumed.</li>
          </ul>
        </Card>
        <Card className="lg:col-span-2" id="data">
          <CardTitle>The data behind the model</CardTitle>
          <DataSources />
        </Card>
        <Card className="lg:col-span-2">
          <CardTitle>Credits</CardTitle>
          <p className="text-sm leading-6 text-muted">
            Visual design inspired by <a className="text-brand-text underline" href="https://github.com/career-ops-hq/career-ops" target="_blank" rel="noreferrer">career-ops</a> (MIT licence).
            Fonts: Inter and Instrument Serif (SIL Open Font License). Built with Next.js, Tailwind CSS, scikit-learn, SHAP and FastAPI.
          </p>
        </Card>
      </div>
    </>
  );
}
