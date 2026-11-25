import { PageHeader } from "@/components/ui";
import { LoginForm } from "./login-form";

export const metadata = { title: "Placement cell sign-in" };

export default async function Login({ searchParams }: { searchParams: Promise<{ next?: string }> }) {
  const { next } = await searchParams;
  return (
    <>
      <PageHeader eyebrow="Placement cell" title="Sign in" />
      <LoginForm next={next ?? "/cell"} />
    </>
  );
}
