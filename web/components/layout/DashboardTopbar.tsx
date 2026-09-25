"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

export default function DashboardTopbar() { // 대시보드에서 공통으로 보이는 상단 바
  const studio = usePathname().startsWith("/dashBoard/presentations");
  return (
    <header className="dashboard-topbar hidden h-16 items-center justify-between border-b border-slate-200 bg-white px-7 md:flex lg:px-9">
      <div>
        <p className="text-sm font-semibold text-slate-900">{studio ? "발표자료 작업실" : "AI비드 업무공간"}</p>
        <p className="mt-0.5 text-xs text-slate-500">{studio ? "나의 양식과 자료로 함께 만드는 프레젠테이션" : "입찰공고 검토부터 제안서 작성까지"}</p>
      </div>
      <Link
        className="rounded-md px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-950"
        href="/mainPage"
      >
        메인으로
      </Link>
    </header>
  );
}
