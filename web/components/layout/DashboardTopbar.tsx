import Link from "next/link";

export default function DashboardTopbar() { // 대시보드에서 공통으로 보이는 상단 바
  return (
    <header className="dashboard-topbar hidden h-16 items-center justify-between border-b border-slate-200 bg-white px-7 md:flex lg:px-9">
      <div>
        <p className="text-sm font-semibold text-slate-900">AI비드 업무공간</p>
        <p className="mt-0.5 text-xs text-slate-500">입찰공고 검토부터 제안서 작성까지</p>
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
