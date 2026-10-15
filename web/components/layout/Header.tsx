"use client";

import Link from "next/link"; // 페이지 이동을 위한 Next.js 링크 컴포넌트
import { useEffect, useState } from "react";
import LogoutButton from "@/components/auth/LogoutButton";

export default function Header({ home = false }: { home?: boolean }) { // 사이트 상단 공통 메뉴 컴포넌트
  const [loggedIn, setLoggedIn] = useState(false);
  useEffect(() => {
    const update = () => setLoggedIn(Boolean(localStorage.getItem("auth_token")));
    const timer = window.setTimeout(update, 0);
    window.addEventListener("storage", update);
    return () => {
      window.clearTimeout(timer);
      window.removeEventListener("storage", update);
    };
  }, []);
  return (
    <header className="sticky top-0 z-50 border-b border-slate-200 bg-white/95 shadow-[0_1px_0_rgb(15_23_42/0.02)] backdrop-blur"> {/* 상단 바 영역 */}
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6"> {/* 로고와 메뉴 배치 */}
        <Link className="flex items-center gap-2.5 text-sm font-bold text-slate-950" href="/mainPage">
          <span aria-hidden="true" className="grid h-8 w-8 place-items-center rounded-md bg-blue-600 text-xs font-bold text-white">AI</span>
          AI비드
        </Link>
        <nav aria-label="상단 메뉴" className="flex items-center gap-1 text-sm text-slate-600 sm:gap-2"> {/* 오른쪽 메뉴 */}
          {home && <div className="mr-4 hidden items-center gap-6 lg:flex"><a href="#product-demo" className="hover:text-blue-700">서비스 시연</a><Link href="#workspaces" className="hover:text-blue-700">작업실</Link><Link href="#questions" className="hover:text-blue-700">자주 묻는 질문</Link></div>}
          <Link className={`${home && !loggedIn ? "hidden sm:block" : ""} rounded-md px-3 py-2 hover:bg-slate-100 hover:text-slate-950`} href="/dashBoard">{loggedIn ? "내 작업실" : "대시보드"}</Link>
          {loggedIn ? <LogoutButton /> : <>
            <Link className="rounded-md px-3 py-2 hover:bg-slate-100 hover:text-slate-950" href="/login">로그인</Link>
            <Link className="rounded-md border border-blue-200 bg-blue-50 px-3 py-2 font-semibold text-blue-700 hover:border-blue-300 hover:bg-blue-100" href="/signup">회원가입</Link>
          </>}
        </nav>
      </div>
    </header>
  );
}
