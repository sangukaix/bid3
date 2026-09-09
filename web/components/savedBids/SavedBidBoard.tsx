"use client"; // 로그인 회원의 저장 공고를 조회하고 화면에서 관리

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import LoginRequiredNotice from "@/components/auth/LoginRequiredNotice";
import BidDetailModal from "@/components/bids/BidDetailModal";
import { API_BASE_URL } from "@/lib/api";
import { formatBidAmount } from "@/lib/bidFormat";
import type { BidNotice, SavedBidResponse } from "@/types/bid";

type SavedBidBoardProps = {
  workflow?: "proposal" | "analysis";
};

export default function SavedBidBoard({
  workflow = "proposal",
}: SavedBidBoardProps) {
  const router = useRouter();
  const [bids, setBids] = useState<BidNotice[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [needsLogin, setNeedsLogin] = useState(false);

  useEffect(() => {
    async function loadSavedBids() {
      const token = localStorage.getItem("auth_token");
      if (!token) {
        setNeedsLogin(true);
        setIsLoading(false);
        return;
      }

      try {
        const response = await fetch(`${API_BASE_URL}/api/saved-bids/`, {
          headers: { Authorization: `Token ${token}` },
        });
        if (response.status === 401 || response.status === 403) {
          setNeedsLogin(true);
          return;
        }
        if (!response.ok) throw new Error();
        const data = (await response.json()) as SavedBidResponse;
        setBids(data.items);
      } catch {
        setError("저장한 공고를 불러오지 못했습니다. Django 서버를 확인해 주세요.");
      } finally {
        setIsLoading(false);
      }
    }

    loadSavedBids();
  }, []);

  async function removeSavedBid(bidNtceNo: string) {
    const confirmed = window.confirm("이 공고의 저장을 취소하시겠습니까?");
    if (!confirmed) return;

    const token = localStorage.getItem("auth_token");
    if (!token) return;
    const response = await fetch(`${API_BASE_URL}/api/saved-bids/${bidNtceNo}/`, {
      method: "DELETE",
      headers: { Authorization: `Token ${token}` },
    });

    if (response.ok) {
      setBids((current) => current.filter((bid) => bid.bidNtceNo !== bidNtceNo));
    } else {
      const data = (await response.json().catch(() => ({}))) as { error?: string };
      setError(data.error ?? "저장 취소에 실패했습니다.");
    }
  }

  async function startProposalProject(bidNtceNo: string) {
    const token = localStorage.getItem("auth_token");
    if (!token) {
      setNeedsLogin(true);
      return;
    }

    const response = await fetch(
      `${API_BASE_URL}/api/saved-bids/${encodeURIComponent(bidNtceNo)}/proposal-project/`,
      {
        method: "POST",
        headers: { Authorization: `Token ${token}` },
      },
    );
    if (!response.ok) {
      setError("제안서 프로젝트를 시작하지 못했습니다.");
      return;
    }

    window.dispatchEvent(new Event("proposal-projects-updated"));
    router.push(`/dashBoard/matchBid/${encodeURIComponent(bidNtceNo)}`);
  }

  if (needsLogin) return <LoginRequiredNotice />;

  const boardTitle =
    workflow === "analysis" ? "성공률 분석할 공고 선택" : "내가 저장한 공고";

  return (
    <section className="app-panel mt-5 overflow-hidden rounded-lg border">
      <div className="flex items-center justify-between border-b border-slate-200 bg-slate-50/60 px-5 py-3.5">
        <h2 className="text-sm font-semibold text-slate-800">{boardTitle}</h2>
        <span className="text-xs tabular-nums text-slate-500">총 {bids.length}건</span>
      </div>

      {isLoading && <p className="px-5 py-14 text-center text-sm text-slate-500">저장한 공고를 불러오는 중입니다.</p>}
      {!isLoading && error && <p className="px-5 py-14 text-center text-sm text-red-600">{error}</p>}
      {!isLoading && !error && bids.length === 0 && (
        <div className="px-5 py-14 text-center">
          <p className="text-sm text-slate-500">아직 저장한 공고가 없습니다.</p>
          <Link className="mt-4 inline-flex rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700" href="/dashBoard/bidList">입찰공고 찾기</Link>
        </div>
      )}

      {bids.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[900px] table-fixed border-collapse text-left text-sm">
            <thead className="bg-slate-50 text-slate-600">
              <tr>
                <th className="w-20 px-3 py-3 font-semibold">구분</th>
                <th className="px-3 py-3 text-center font-semibold">공고명</th>
                <th className="w-24 px-3 py-3 font-semibold">계약 방법</th>
                <th className="w-32 px-3 py-3 font-semibold">예산/추정가격</th>
                <th className="w-24 px-3 py-3 font-semibold">마감일</th>
                <th className="w-[210px] px-3 py-3 text-center font-semibold">작업</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {bids.map((bid) => {
                const isAnalysis = workflow === "analysis";
                const hasResult = isAnalysis ? bid.hasAnalysis : bid.hasProposal;
                const href = isAnalysis
                  ? `/dashBoard/matchBid/analysis?bid=${encodeURIComponent(bid.bidNtceNo)}`
                  : `/dashBoard/matchBid/${encodeURIComponent(bid.bidNtceNo)}`;

                return (
                  <tr className="hover:bg-slate-50" key={`${bid.bidNtceNo}-${bid.bidNtceOrd}`}>
                    <td className="px-3 py-4 text-slate-600">{bid.bsnsDivNm || "-"}</td>
                    <td className="px-3 py-4">
                      <div className="leading-5">
                        <BidDetailModal bid={bid} flowTrigger trigger={bid.bidNtceNm} triggerClassName="inline cursor-pointer break-keep text-left font-semibold text-slate-950 hover:text-blue-600" />
                        {typeof bid.bidNtceUrl === "string" && bid.bidNtceUrl ? (
                          <>
                            {" "}
                            <a className="inline-flex h-6 items-center rounded-md border border-slate-300 px-2 align-middle text-[11px] font-semibold text-slate-600 hover:border-blue-400 hover:text-blue-600" href={bid.bidNtceUrl} rel="noreferrer" target="_blank">원문</a>
                          </>
                        ) : null}
                      </div>
                    </td>
                    <td className="px-3 py-4 text-slate-600">{bid.cntrctCnclsMthdNm || "-"}</td>
                    <td className="px-3 py-4 text-slate-600">{formatBidAmount(bid)}</td>
                    <td className="px-3 py-4 text-slate-600">{bid.bidClseDate || "확인 필요"}</td>
                    <td className="px-3 py-4">
                      <div className="flex items-center justify-center gap-2 whitespace-nowrap">
                        {isAnalysis ? (
                          <Link
                            className="inline-flex h-10 w-[112px] flex-col items-center justify-center rounded-md bg-blue-600 text-xs font-semibold leading-4 text-white transition hover:bg-blue-700"
                            href={href}
                          >
                            <span>분석하기</span>
                            {hasResult && (
                              <span className="text-[10px] font-normal text-blue-100">
                                다시보기
                              </span>
                            )}
                          </Link>
                        ) : bid.isProposalTrashed ? (
                          <Link
                            className="inline-flex h-10 w-[112px] flex-col items-center justify-center rounded-md border border-slate-300 bg-slate-50 text-xs font-semibold leading-4 text-slate-600 transition hover:bg-slate-100"
                            href="/dashBoard/trash"
                          >
                            <span>휴지통에서 복원</span>
                          </Link>
                        ) : (
                          <button
                            className="inline-flex h-10 w-[112px] cursor-pointer flex-col items-center justify-center rounded-md bg-blue-600 text-xs font-semibold leading-4 text-white transition hover:bg-blue-700"
                            onClick={() => void startProposalProject(bid.bidNtceNo)}
                            type="button"
                          >
                            <span>제안서 만들기</span>
                            {hasResult && (
                              <span className="text-[10px] font-normal text-blue-100">
                                이어가기
                              </span>
                            )}
                          </button>
                        )}
                        <button
                          className="h-9 w-[72px] rounded-md border border-red-200 text-xs font-semibold text-red-600 hover:bg-red-50 disabled:cursor-not-allowed disabled:border-slate-200 disabled:text-slate-300 disabled:hover:bg-white"
                          disabled={Boolean(bid.isProposalTrashed)}
                          onClick={() => removeSavedBid(bid.bidNtceNo)}
                          title={bid.isProposalTrashed ? "프로젝트를 영구 삭제한 뒤 저장을 취소할 수 있습니다." : undefined}
                          type="button"
                        >
                          저장 취소
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
