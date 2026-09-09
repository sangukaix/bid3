import Sidebar from "@/components/layout/Sidebar"; // 대시보드 왼쪽 메뉴 컴포넌트

import DashboardTopbar from "@/components/layout/DashboardTopbar";

type DashBoardLayoutProps = { // layout이 받을 props 타입
  children: React.ReactNode; // 현재 선택된 페이지 내용이 들어오는 자리
};

export default function DashBoardLayout({ children }: DashBoardLayoutProps) { // /dashBoard 아래 페이지들의 공통 화면 틀
  return (
    <main className="min-h-screen bg-transparent text-slate-950"> {/* 대시보드 전체 배경 영역 */}
      <div className="dashboard-shell min-h-screen md:grid md:grid-cols-[224px_minmax(0,1fr)]"> {/* 고정 메뉴와 본문을 나누는 공통 틀 */}
        <Sidebar /> {/* 모든 대시보드 페이지에서 공통으로 보이는 왼쪽 메뉴 */}
        <div className="min-w-0">
          <DashboardTopbar /> {/* 대시보드 공통 상단 바 */}
          <div className="dashboard-content min-w-0 px-3 py-5 sm:px-5 md:px-7 md:py-7 lg:px-9">
            <div className="mx-auto w-full max-w-[1360px]">{children}</div> {/* 각 page.tsx의 내용이 바뀌어 들어오는 자리 */}
          </div>
        </div>
      </div>
    </main>
  );
}
