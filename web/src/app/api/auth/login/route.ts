import { adminPassword, checkPassword, COOKIE, makeSession, SESSION_HOURS } from "@/lib/auth";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(req: Request) {
  const password = adminPassword();
  if (!password) return Response.json({ ok: true, enabled: false });
  let given = "";
  try {
    const body = (await req.json()) as { password?: unknown };
    given = typeof body.password === "string" ? body.password : "";
  } catch { /* empty body */ }
  if (!(await checkPassword(given, password))) {
    await new Promise((r) => setTimeout(r, 400)); // slow down guessing
    return Response.json({ detail: "Incorrect password." }, { status: 401 });
  }
  const secure = new URL(req.url).protocol === "https:" || req.headers.get("x-forwarded-proto") === "https";
  const cookie = [`${COOKIE}=${await makeSession(password)}`, "Path=/", "HttpOnly", "SameSite=Lax",
    `Max-Age=${SESSION_HOURS * 3600}`, secure ? "Secure" : ""].filter(Boolean).join("; ");
  return new Response(JSON.stringify({ ok: true }), { headers: { "content-type": "application/json", "set-cookie": cookie } });
}
