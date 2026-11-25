import { PageHeader } from "@/components/ui";
import { ProfileView } from "./profile-view";

export const metadata = { title: "My profile & CV" };

export default function Profile() {
  return (
    <>
      <PageHeader eyebrow="Student / Profile" title="My profile & CV">
        Your CV and campus details feed the readiness model. Everything stays on this computer unless you choose to share.
      </PageHeader>
      <ProfileView />
    </>
  );
}
