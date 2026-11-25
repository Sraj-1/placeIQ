// Placement-cell sign-in. Enabled only when PLACEIQ_ADMIN_PASSWORD is set (e.g. as a secret on
// the hosting platform); local use without it stays open. The session cookie is
// "<expiry>.<HMAC-SHA256(password, 'placeiq:<expiry>')>", so changing the password signs
// everyone out. Web Crypto only, so it works in the proxy and in route handlers.

export const COOKIE = "placeiq_cell";
export const SESSION_HOURS = 12;

export function adminPassword(): string | null {
  const p = process.env.PLACEIQ_ADMIN_PASSWORD;
  return p && p.length > 0 ? p : null;
}

async function hmac(key: string, msg: string): Promise<string> {
  const k = await crypto.subtle.importKey("raw", new TextEncoder().encode(key), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const sig = await crypto.subtle.sign("HMAC", k, new TextEncoder().encode(msg));
  return Array.from(new Uint8Array(sig), (b) => b.toString(16).padStart(2, "0")).join("");
}

function safeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

export async function makeSession(password: string): Promise<string> {
  const exp = Date.now() + SESSION_HOURS * 3600_000;
  return `${exp}.${await hmac(password, `placeiq:${exp}`)}`;
}

export async function validSession(value: string | undefined, password: string): Promise<boolean> {
  if (!value) return false;
  const [expStr, sig] = value.split(".");
  const exp = Number(expStr);
  if (!Number.isFinite(exp) || exp < Date.now() || !sig) return false;
  return safeEqual(sig, await hmac(password, `placeiq:${exp}`));
}

export async function checkPassword(given: string, password: string): Promise<boolean> {
  // Compare digests so the comparison time doesn't depend on where the strings differ.
  return safeEqual(await hmac("placeiq-login", given), await hmac("placeiq-login", password));
}

export function isProtectedPath(pathname: string): boolean {
  return pathname === "/cell" || pathname.startsWith("/cell/") || pathname.startsWith("/api/engine/admin");
}
