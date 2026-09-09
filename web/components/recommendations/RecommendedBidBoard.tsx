"use client"; // 로그인 토큰으로 회원별 추천 공고를 불러오는 화면

import { useEffect, useState } from "react";

import LoginRequiredNotice from "@/components/auth/LoginRequiredNotice";
import BidDetailModal from "@/components/bids/BidDetailModal";
import SaveBidButton from "@/components/bids/SaveBidButton";
import { API_BASE_URL } from "@/lib/api";
import { formatBidAmount } from "@/lib/bidFormat";
import type { BidNotice, StoredRecommendationResponse } from "@/types/bid";

function MatchScoreDialog({ bid, onClose }: { bid: BidNotice; onClose: () => void }) {
  const reasons = bid.matchReasons ?? [];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/35 px-4">
      <section
        aria-labelledby="match-score-title"
        aria-modal="true"
        className="w-full max-w-md rounded-lg border border-slate-200 bg-white p-6 shadow-xl"
        role="dialog"
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold text-blue-600">조건 일치도</p>
            <h2 className="mt-1 text-lg font-bold text-slate-950" id="match-score-title">
              추천 조건 분석
            </h2>
          </div>
          <button
            aria-label="조건 일치도 팝업 닫기"
            className="flex h-8 w-8 items-center justify-center rounded-md text-xl text-slate-400 hover:bg-slate-100 hover:text-slate-700"
            onClick={onClose}
            type="button"
          >
            ×
          </button>
        </div>

        <div className="mt-5 flex items-center gap-3 rounded-md bg-blue-50 px-4 py-3">
          <strong className="text-xl text-blue-700">{bid.matchScore ?? 0}점</strong>
          <span className="text-xs text-blue-700">회사 정보와 공고 조건의 일치 점수입니다.</span>
        </div>

        <ul className="mt-5 space-y-2 text-sm leading-6 text-slate-600">
          {reasons.length > 0 ? reasons.map((reason) => (
            <li className="border-b border-slate-100 pb-2 last:border-0" key={reason}>
              {reason}
            </li>
          )) : (
            <li>회사 정보와 일치한 조건이 있는 추천 공고입니다.</li>
          )}
        </ul>

        <p className="mt-4 text-xs text-slate-400">
          조건 일치도는 낙찰 확률이 아니며, 참가 자격은 공고문을 별도로 확인해야 합니다.
        </p>
      </section>
    </div>
  );
}

export default function RecommendedBidBoard() {
  const [data, setData] = useState<StoredRecommendationResponse | null>(null);
  const [error, setError] = useState("");
  const [needsLogin, setNeedsLogin] = useState(false);
  const [businessType, setBusinessType] = useState(""); // 추천 목록에서 선택한 업무 구분
  const [deadlineSort, setDeadlineSort] = useState<"asc" | "desc">("asc"); // 마감일 빠른순·느린순
  const [selectedScoreBid, setSelectedScoreBid] = useState<BidNotice | null>(null); // 점수 설명 팝업에 표시할 공고

  useEffect(() => {
    async function loadRecommendations() {
      const token = localStorage.getItem("auth_token");
      if (!token) {
        setNeedsLogin(true);
        return;
      }

      try {
        const response = await fetch(`${API_BASE_URL}/api/recommendations/`, {
          headers: { Authorization: `Token ${token}` },
        });
        if (response.status === 401 || response.status === 403) {
          setNeedsLogin(true);
          return;
        }
        if (!response.ok) throw new Error();
        setData((await response.json()) as StoredRecommendationResponse);
      } catch {
        setError("추천 공고를 불러오지 못했습니다. Django 서버를 확인해 주세요.");
      }
    }

    loadRecommendations();
  }, []);

  if (needsLogin) {
    return <LoginRequiredNotice />;
  }
  if (error) {
    return <p className="mt-6 rounded-md bg-red-50 px-5 py-12 text-center text-sm text-red-600">{error}</p>;
  }
  if (!data) {
    return <p className="mt-6 py-12 text-center text-sm text-slate-500">추천 공고를 불러오는 중입니다.</p>;
  }

  const filteredItems = data.items.filter(
    (bid) => !businessType || bid.bsnsDivNm === businessType,
  ); // 전체·물품·용역·공사 중 선택한 공고만 표시
  const sortedItems = [...filteredItems].sort((first, second) => {
    if (!first.bidClseDate) return 1;
    if (!second.bidClseDate) return -1;

    return deadlineSort === "asc"
      ? first.bidClseDate.localeCompare(second.bidClseDate)
      : second.bidClseDate.localeCompare(first.bidClseDate);
  }); // 화면에 표시할 목록만 복사해서 마감일순으로 정렬

  return (
    <section className="app-panel mt-5 overflow-hidden rounded-lg border">
      <div className="flex items-center justify-between border-b border-slate-200 bg-slate-50/60 px-5 py-3.5">
        <h2 className="text-sm font-semibold text-slate-800">AI 추천 공고</h2>
        <span className="text-xs tabular-nums text-slate-500">총 {sortedItems.length}건</span>
      </div>

      {sortedItems.length === 0 ? (
        <div className="px-5 py-14 text-center text-sm text-slate-500">
          {data.items.length === 0
            ? "아직 조건에 맞는 새 공고가 없습니다. 회사 정보의 희망 조건을 확인해 주세요."
            : "선택한 구분에 해당하는 추천 공고가 없습니다."}
        </div>
      ) : (
        <>
          <p className="border-b border-slate-200 px-4 py-2 text-right text-xs text-slate-400">
            마감일이 지난 공고는 자동으로 삭제됩니다.
          </p>

          <div className="overflow-x-auto">
            <table className="w-full min-w-[980px] table-fixed border-collapse text-left text-sm">
              <thead className="bg-slate-50 text-slate-600">
                <tr>
                  <th className="w-24 whitespace-nowrap px-4 py-3 font-semibold">
                    <label className={`relative inline-flex cursor-pointer items-center gap-1 ${businessType ? "text-blue-600" : ""}`}>
                      <span>구분</span>
                      <span aria-hidden="true" className="text-xs">▾</span>
                      <select
                        aria-label="추천 공고 업무 구분 필터"
                        className="absolute inset-0 h-full w-full cursor-pointer opacity-0"
                        onChange={(event) => setBusinessType(event.target.value)}
                        value={businessType}
                      >
                        <option value="">전체</option>
                        <option value="물품">물품</option>
                        <option value="용역">용역</option>
                        <option value="공사">공사</option>
                      </select>
                    </label>
                  </th>
                  <th className="px-4 py-3 text-center font-semibold">공고명</th>
                  <th className="w-28 px-4 py-3 font-semibold">
                    <span className="group relative inline-flex items-center gap-1">
                      <span className="text-center leading-4">조건<br />일치도</span>
                      <button aria-label="조건 일치도 계산 기준" className="flex h-4 w-4 cursor-help items-center justify-center rounded-full border border-slate-400 text-[10px] text-slate-500" type="button">?</button>
                      <span className="invisible absolute left-0 top-6 z-20 w-72 rounded-md bg-slate-900 px-3 py-2 text-xs font-normal leading-5 text-white opacity-0 shadow-lg transition group-hover:visible group-hover:opacity-100 group-focus-within:visible group-focus-within:opacity-100">
                        공고명은 첫 키워드 40점·추가 키워드당 10점(최대 60점), 업종·기관은 첫 키워드 10점·추가 키워드당 5점(최대 15점)입니다. 업무 구분과 희망 지역은 각 10점, 금액 범위는 5점입니다. 동점이면 공고명 일치 개수, 최신 등록일, 마감일 순으로 정렬합니다.
                      </span>
                    </span>
                  </th>
                  <th className="w-32 px-4 py-3 font-semibold">예산/추정가격</th>
                  <th className="w-28 px-4 py-3 font-semibold">
                    <label className="relative inline-flex cursor-pointer items-center gap-1">
                      <span>마감일</span>
                      <span aria-hidden="true" className="text-xs">▾</span>
                      <select
                        aria-label="추천 공고 마감일 정렬"
                        className="absolute inset-0 h-full w-full cursor-pointer opacity-0"
                        onChange={(event) => setDeadlineSort(event.target.value as "asc" | "desc")}
                        value={deadlineSort}
                      >
                        <option value="asc">오름차순</option>
                        <option value="desc">내림차순</option>
                      </select>
                    </label>
                  </th>
                  <th className="w-24 px-4 py-3 text-center font-semibold">저장</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {sortedItems.map((bid) => (
                  <tr className="hover:bg-slate-50" key={`${bid.bidNtceNo}-${bid.bidNtceOrd}`}>
                    <td className="px-4 py-4 text-slate-600">{bid.bsnsDivNm || "-"}</td>
                    <td className="px-4 py-4">
                      <div className="leading-5">
                        <BidDetailModal bid={bid} flowTrigger trigger={bid.bidNtceNm} triggerClassName="inline cursor-pointer break-keep text-left font-semibold text-slate-950 hover:text-blue-600" />
                        {typeof bid.bidNtceUrl === "string" && bid.bidNtceUrl ? (
                          <>
                            {" "}
                            <a className="inline-flex h-6 items-center rounded-md border border-slate-300 px-2 align-middle text-[11px] font-semibold text-slate-600 hover:border-blue-400 hover:text-blue-600" href={bid.bidNtceUrl} rel="noreferrer" target="_blank">원문</a>
                          </>
                        ) : null}
                      </div>
                      <p className="mt-1 text-xs text-slate-500">{bid.matchReasons?.join(" · ") || "회사 조건 일치"}</p>
                    </td>
                    <td className="px-4 py-4">
                      <button
                        aria-haspopup="dialog"
                        className="rounded-md bg-blue-50 px-2.5 py-1 text-sm font-semibold text-blue-700 transition-colors hover:bg-blue-100 hover:text-blue-800"
                        onClick={() => setSelectedScoreBid(bid)}
                        type="button"
                      >
                        {bid.matchScore ?? 0}점
                      </button>
                    </td>
                    <td className="px-4 py-4 text-slate-600">{formatBidAmount(bid)}</td>
                    <td className="px-4 py-4 text-slate-600">{bid.bidClseDate || "확인 필요"}</td>
                    <td className="px-4 py-4 text-center"><SaveBidButton bidNtceNo={bid.bidNtceNo} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {selectedScoreBid && (
        <MatchScoreDialog bid={selectedScoreBid} onClose={() => setSelectedScoreBid(null)} />
      )}
    </section>
  );
}
