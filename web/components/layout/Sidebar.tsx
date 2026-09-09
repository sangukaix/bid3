"use client";

import Link from "next/link"; // 페이지 이동을 위한 Next.js 링크 컴포넌트
import { usePathname } from "next/navigation"; // 현재 보고 있는 페이지 주소 확인
import { useCallback, useEffect, useState } from "react";

import LogoutButton from "@/components/auth/LogoutButton"; // 로그인 정보 삭제 버튼
import { API_BASE_URL } from "@/lib/api";
import type { BidNotice, SavedBidResponse } from "@/types/bid";

const menuItems = [ // 사이드바의 기본 메뉴 목록
  { href: "/dashBoard/myCompanyInfo", label: "회사정보" },
  { href: "/dashBoard/bidList", label: "입찰공고 목록" },
  { href: "/dashBoard/recommendedBid", label: "추천공고" },
];

const mobileMenuItems = [ // 모바일에서는 핵심 화면을 한 줄 메뉴로 간단히 표시
  ...menuItems,
  { href: "/dashBoard/matchBid", label: "제안서 제작" },
  { href: "/dashBoard/trash", label: "휴지통" },
  { href: "/dashBoard/myInfo", label: "결제 정보" },
];

export default function Sidebar() { // 대시보드에서 공통으로 쓰는 왼쪽 메뉴
  const pathname = usePathname();
  const [proposalProjects, setProposalProjects] = useState<BidNotice[]>([]);
  const isProposalPage = pathname.startsWith("/dashBoard/matchBid");
  const currentProjectId =
    isProposalPage && !pathname.startsWith("/dashBoard/matchBid/analysis")
      ? decodeURIComponent(pathname.split("/")[3] ?? "")
      : "";

  const loadProposalProjects = useCallback(async () => {
    const token = localStorage.getItem("auth_token");
    if (!token) {
      setProposalProjects([]);
      return;
    }
    try {
      const response = await fetch(`${API_BASE_URL}/api/saved-bids/`, {
        headers: { Authorization: `Token ${token}` },
      });
      if (!response.ok) return;
      const data = (await response.json()) as SavedBidResponse;
      setProposalProjects(
        data.items
          .filter((item) => item.hasProposalProject)
          .sort((first, second) => {
            const firstTime =
              first.proposalProjectStartedAt ?? first.savedAt ?? "";
            const secondTime =
              second.proposalProjectStartedAt ?? second.savedAt ?? "";
            return firstTime.localeCompare(secondTime);
          }),
      ); // 프로젝트를 시작한 순서대로 프로젝트 1, 2 번호 유지
    } catch {
      // 사이드바 목록 실패는 현재 페이지 사용을 막지 않음
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(
      () => void loadProposalProjects(),
      0,
    );
    window.addEventListener("proposal-projects-updated", loadProposalProjects);
    return () => {
      window.clearTimeout(timer);
      window.removeEventListener(
        "proposal-projects-updated",
        loadProposalProjects,
      );
    };
  }, [loadProposalProjects]);

  function isMenuCurrent(href: string) {
    return pathname === href || pathname.startsWith(`${href}/`);
  }

  function menuClassName(href: string) {
    const isCurrent = isMenuCurrent(href);

    return `flex h-10 items-center gap-2 whitespace-nowrap rounded-md px-3 text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-300 ${
      isCurrent
        ? "bg-blue-50 font-semibold text-blue-700 shadow-[inset_3px_0_0_#2563eb]"
        : "text-slate-600 hover:bg-slate-50 hover:text-slate-950"
    }`;
  }

  return (
    <>
      {/* 모바일에서는 긴 사이드바 대신 가로 스크롤 메뉴를 사용합니다. */}
      <aside className="sticky top-0 z-40 overflow-hidden border-b border-slate-200 bg-white md:hidden">
        <div className="flex h-12 items-center justify-between border-b border-slate-200 px-3">
          <div className="flex items-center gap-2">
            <span aria-hidden="true" className="grid h-7 w-7 place-items-center rounded-md bg-blue-600 text-[10px] font-bold text-white">AI</span>
            <p className="text-sm font-bold text-slate-950">Dashboard</p>
          </div>
          <div className="flex items-center gap-1">
            <Link className="rounded-md px-2 py-1.5 text-xs text-slate-600 hover:bg-slate-100 hover:text-slate-950" href="/mainPage">
              메인
            </Link>
            <div className="[&_button]:whitespace-nowrap [&_button]:px-2 [&_button]:py-1.5 [&_button]:text-xs">
              <LogoutButton />
            </div>
          </div>
        </div>
        <nav className="mobile-dashboard-nav flex gap-1 overflow-x-auto px-2 py-2" aria-label="모바일 대시보드 메뉴">
          {mobileMenuItems.map((item) => {
            const isCurrent = isMenuCurrent(item.href);
            return (
              <Link
                aria-current={isCurrent ? "page" : undefined}
                className={`shrink-0 rounded-md px-3 py-2 text-xs font-medium ${
                  isCurrent
                    ? "bg-blue-50 text-blue-700"
                    : "text-slate-600 hover:bg-slate-100 hover:text-slate-950"
                }`}
                href={item.href}
                key={item.href}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
      </aside>

      {/* 데스크톱에서는 메뉴와 프로젝트를 고정된 사이드바에 표시합니다. */}
      <aside className="hidden flex-col overflow-hidden border-r border-slate-200 bg-white p-3 md:sticky md:top-0 md:flex md:h-screen lg:p-4">
        <div className="mb-4 flex h-12 items-center gap-3 border-b border-slate-200 px-2 pb-4">
          <span aria-hidden="true" className="grid h-8 w-8 shrink-0 place-items-center rounded-md bg-blue-600 text-[11px] font-bold text-white">AI</span>
          <div className="min-w-0">
            <p className="text-[15px] font-bold text-slate-950">Dashboard</p>
            <p className="mt-0.5 text-[11px] text-slate-400">AI비드</p>
          </div>
        </div>

        <nav className="min-h-0 flex-1 space-y-1 overflow-y-auto pr-1" aria-label="대시보드 메뉴"> {/* 메뉴 링크 목록 */}
          {menuItems.map((item) => {
            const isCurrent = isMenuCurrent(item.href);

            return (
              <Link
                aria-current={isCurrent ? "page" : undefined}
                className={menuClassName(item.href)}
                href={item.href}
                key={item.href}
              >
                <span aria-hidden="true" className="w-0.5" />
                {item.label}
              </Link>
            );
          })}

          <div>
            <Link
              aria-current={isProposalPage ? "page" : undefined}
              className={menuClassName("/dashBoard/matchBid")}
              href="/dashBoard/matchBid"
            >
              <span aria-hidden="true" className="w-0.5" />
              제안서 제작
            </Link>

            {proposalProjects.length > 0 && (
              <div className="ml-5 mt-1 border-l border-slate-200 pl-2">
                {proposalProjects.map((project, index) => {
                  const isCurrent = currentProjectId === project.bidNtceNo;
                  return (
                    <Link
                      aria-current={isCurrent ? "page" : undefined}
                      className={`mt-1 block rounded-md px-3 py-2 transition-colors ${
                        isCurrent
                          ? "bg-slate-100 font-semibold text-slate-900"
                          : "text-slate-500 hover:bg-slate-100 hover:text-slate-800"
                      }`}
                      href={`/dashBoard/matchBid/${encodeURIComponent(project.bidNtceNo)}`}
                      key={project.bidNtceNo}
                      title={`프로젝트${index + 1} ${project.bidNtceNm}`}
                    >
                      <span className="block text-xs font-semibold">프로젝트{index + 1}</span>
                      <span className="mt-0.5 block overflow-hidden text-ellipsis whitespace-nowrap text-[11px] leading-4 opacity-75">
                        {project.bidNtceNm}
                      </span>
                    </Link>
                  );
                })}
              </div>
            )}
          </div>
        </nav>

        <div className="mt-3 space-y-1 border-t border-slate-200 pt-3">
          <Link
            aria-current={pathname === "/dashBoard/trash" ? "page" : undefined}
            className={menuClassName("/dashBoard/trash")}
            href="/dashBoard/trash"
          >
            <span aria-hidden="true" className="w-0.5" />
            휴지통
          </Link>

          <Link
            aria-current={pathname === "/dashBoard/myInfo" ? "page" : undefined}
            className={menuClassName("/dashBoard/myInfo")}
            href="/dashBoard/myInfo"
          >
            <span aria-hidden="true" className="w-0.5" />
            결제 정보
          </Link>

          <nav className="mt-2 flex flex-col border-t border-slate-200 pt-2">
            <LogoutButton />
          </nav>
        </div>
      </aside>
    </>
  );
}
