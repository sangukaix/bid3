import Link from "next/link"; // 페이지 이동을 위한 Next.js 링크 컴포넌트

export default function Header() { // 사이트 상단 공통 메뉴 컴포넌트
  return (
    <header className="sticky top-0 z-50 border-b border-slate-200 bg-white/95 shadow-[0_1px_0_rgb(15_23_42/0.02)] backdrop-blur"> {/* 상단 바 영역 */}
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6"> {/* 로고와 메뉴 배치 */}
        <Link className="flex items-center gap-2.5 text-sm font-bold text-slate-950" href="/mainPage">
          <span aria-hidden="true" className="grid h-8 w-8 place-items-center rounded-md bg-blue-600 text-xs font-bold text-white">AI</span>
          AI비드
        </Link>
        <nav className="flex items-center gap-1 text-sm text-slate-600 sm:gap-2"> {/* 오른쪽 메뉴 */}
          <Link className="rounded-md px-3 py-2 hover:bg-slate-100 hover:text-slate-950" href="/dashBoard">대시보드</Link>
          <Link className="rounded-md px-3 py-2 hover:bg-slate-100 hover:text-slate-950" href="/login">로그인</Link>
          <Link className="rounded-md border border-blue-200 bg-blue-50 px-3 py-2 font-semibold text-blue-700 hover:border-blue-300 hover:bg-blue-100" href="/signup">회원가입</Link>
        </nav>
      </div>
    </header>
  );
}
