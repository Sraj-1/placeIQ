import { cookies } from "next/headers";
import { adminPassword, COOKIE, validSession } from "@/lib/auth";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET() {
  const password = adminPassword();
  if (!password) return Response.json({ enabled: false, signedIn: true });
  const value = (await cookies()).get(COOKIE)?.value;
  return Response.json({ enabled: true, signedIn: await validSession(value, password) });
}
