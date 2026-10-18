import { createHash, createHmac, timingSafeEqual } from "node:crypto";

export const demoCookieName = "bid3_demo_access";
export const demoSessionSeconds = 8 * 60 * 60;

export function demoEnabled() {
  return process.env.BID3_PUBLIC_DEMO_BUILD === "1" || process.env.BID3_PUBLIC_DEMO === "1";
}

export function demoConfigured() {
  return (process.env.BID3_DEMO_PASSWORD?.length ?? 0) >= 24
    && (process.env.BID3_DEMO_SIGNING_KEY?.length ?? 0) >= 32
    && /^https:\/\/[^/]+$/.test(process.env.BID3_DEMO_ORIGIN ?? "");
}

export function passwordMatches(value: string) {
  if (!demoConfigured() || value.length > 256) return false;
  const hash = (text: string) => createHash("sha256").update(text).digest();
  return timingSafeEqual(hash(value), hash(process.env.BID3_DEMO_PASSWORD!));
}

function signature(expires: string) {
  return createHmac("sha256", process.env.BID3_DEMO_SIGNING_KEY!)
    .update(`bid3-demo-v1:${expires}`).digest("base64url");
}

export function createAccessToken(now = Date.now()) {
  if (!demoConfigured()) throw new Error("Public demo access is not configured.");
  const expires = String(Math.floor(now / 1000) + demoSessionSeconds);
  return `${expires}.${signature(expires)}`;
}

export function validAccessToken(token: string | undefined, now = Date.now()) {
  if (!demoConfigured() || !token || token.length > 100) return false;
  const match = /^(\d{10})\.([A-Za-z0-9_-]{43})$/.exec(token);
  if (!match) return false;
  const seconds = Math.floor(now / 1000);
  const expires = Number(match[1]);
  if (expires <= seconds || expires > seconds + demoSessionSeconds) return false;
  return timingSafeEqual(Buffer.from(match[2]), Buffer.from(signature(match[1])));
}
