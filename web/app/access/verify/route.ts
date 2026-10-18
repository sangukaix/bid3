import { NextResponse, type NextRequest } from "next/server";
import { createAccessToken, demoConfigured, demoCookieName, demoEnabled, demoInviteRequired, demoSessionSeconds, passwordMatches } from "../../../lib/demo-access";

export const dynamic = "force-dynamic";
const headers = { "Cache-Control": "private, no-store", "X-Robots-Tag": "noindex, nofollow" };
let failureWindow = 0;
let failures = 0;

export async function POST(request: NextRequest) {
  if (!demoEnabled()) return new NextResponse(null, { status: 404 });
  if (!demoConfigured()) return new NextResponse(null, { status: 503, headers });
  if (!demoInviteRequired()) return new NextResponse(null, { status: 404, headers });
  if (request.headers.get("origin") !== process.env.BID3_DEMO_ORIGIN) {
    return new NextResponse(null, { status: 403, headers });
  }
  if (!request.headers.get("content-type")?.startsWith("application/x-www-form-urlencoded")) {
    return new NextResponse(null, { status: 415, headers });
  }
  const now = Date.now();
  if (now - failureWindow >= 60_000) { failureWindow = now; failures = 0; }
  if (failures >= 10) {
    return new NextResponse("잠시 후 다시 시도해 주세요.", { status: 429, headers: { ...headers, "Retry-After": "60" } });
  }
  const reader = request.body?.getReader();
  let body = "";
  let size = 0;
  const decoder = new TextDecoder();
  if (reader) {
    while (true) {
      const chunk = await reader.read();
      if (chunk.done) break;
      size += chunk.value.byteLength;
      if (size > 4096) { await reader.cancel(); return new NextResponse(null, { status: 413, headers }); }
      body += decoder.decode(chunk.value, { stream: true });
    }
    body += decoder.decode();
  }
  if (!passwordMatches(new URLSearchParams(body).get("password") ?? "")) {
    failures += 1;
    return NextResponse.redirect(new URL("/access?error=1", process.env.BID3_DEMO_ORIGIN), { status: 303, headers });
  }
  const response = NextResponse.redirect(new URL("/mainPage", process.env.BID3_DEMO_ORIGIN), { status: 303, headers });
  response.cookies.set(demoCookieName, createAccessToken(now), {
    httpOnly: true, secure: true, sameSite: "strict", path: "/", maxAge: demoSessionSeconds,
  });
  return response;
}
