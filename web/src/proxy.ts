import { NextResponse, type NextRequest } from "next/server";
import { adminPassword, COOKIE, isProtectedPath, validSession } from "@/lib/auth";

// Guards the placement-cell pages and the engine's admin API when a password is configured.
export async function proxy(req: NextRequest) {
  const password = adminPassword();
  const { pathname, search } = req.nextUrl;
  if (!password || !isProtectedPath(pathname)) return NextResponse.next();
  if (await validSession(req.cookies.get(COOKIE)?.value, password)) return NextResponse.next();
  if (pathname.startsWith("/api/")) {
    return NextResponse.json({ detail: "Placement-cell sign-in required." }, { status: 401 });
  }
  const url = req.nextUrl.clone();
  url.pathname = "/login";
  url.search = `?next=${encodeURIComponent(pathname + search)}`;
  return NextResponse.redirect(url);
}

export const config = { matcher: ["/cell", "/cell/:path*", "/api/engine/admin/:path*"] };
