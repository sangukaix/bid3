import { NextResponse, type NextRequest } from "next/server";
import { demoConfigured, demoCookieName, demoEnabled, validAccessToken } from "./lib/demo-access";

export function proxy(request: NextRequest) {
  if (!demoEnabled()) return NextResponse.next();
  const headers = { "Cache-Control": "private, no-store", "X-Robots-Tag": "noindex, nofollow" };
  if (!demoConfigured()) {
    return new NextResponse("외부 시연 접속 설정을 확인해 주세요.", { status: 503, headers });
  }
  const path = request.nextUrl.pathname;
  if (path === "/access" || path === "/access/verify" || path.startsWith("/_next/static/") || path === "/favicon.ico") {
    return NextResponse.next({ headers });
  }
  if (validAccessToken(request.cookies.get(demoCookieName)?.value)) {
    return NextResponse.next({ headers });
  }
  if (path.startsWith("/api/") || !["GET", "HEAD"].includes(request.method)) {
    return NextResponse.json({ error: "초대 암호로 접속한 뒤 이용해 주세요." }, { status: 401, headers });
  }
  return NextResponse.redirect(new URL("/access", process.env.BID3_DEMO_ORIGIN), { status: 307, headers });
}
