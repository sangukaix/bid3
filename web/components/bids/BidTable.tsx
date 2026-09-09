"use client"; // 표 제목의 구분 필터와 마감일 정렬을 브라우저에서 처리

import Link from "next/link";
import { useRouter } from "next/navigation";

import type { BidApiResponse, BidNotice, BidSearchParams } from "@/types/bid"; // 입찰공고 한 건의 TypeScript 자료형 가져오기
import BidDetailModal from "@/components/bids/BidDetailModal";
import SaveBidButton from "@/components/bids/SaveBidButton";
import { formatBidAmount } from "@/lib/bidFormat";

type BidTableProps = {
  data: BidApiResponse | null;
  error: string | null;
  filters: BidSearchParams;
};


function getDeadlineParts(bid: BidNotice) {
  if (!bid.bidClseDate) {
    return { date: "-", time: "" };
  }

  const date = bid.bidClseDate.replaceAll("-", ".");
  return { date, time: bid.bidClseTm || "" };
}


function formatNoticeDate(bid: BidNotice) {
  return bid.bidNtceDate ? bid.bidNtceDate.replaceAll("-", ".") : "-";
}

function formatNoticeOrganization(bid: BidNotice) {
  return bid.ntceInsttNm || bid.dminsttNm || "확인 필요";
}


function formatAllowedRegion(bid: BidNotice) {
  return bid.regionLimit ? bid.allowedRegion || "확인 필요" : "전국";
}


function RegionInfo({ bid }: { bid: BidNotice }) {
  const region = formatAllowedRegion(bid);
  const regionParts = [...new Set(region.split(/[,/\n]+/).map((item) => item.trim()).filter(Boolean))];
  const preview = regionParts.slice(0, 2).join(", ") || region;
  const needsTooltip = regionParts.length > 2 || preview.length > 14;

  if (!needsTooltip) {
    return (
      <p className="mt-1 max-w-20 truncate whitespace-nowrap text-xs leading-4 text-slate-500">
        {region}
      </p>
    );
  }

  return (
    <span className="group relative mt-1 block max-w-20">
      <button
        aria-label={`참가 지역 확인: ${region}`}
        className="flex w-full cursor-help items-center gap-1 text-left text-xs text-slate-500 hover:text-blue-600"
        type="button"
      >
        <span className="min-w-0 truncate whitespace-nowrap leading-4">{preview}</span>
        <span aria-hidden="true" className="shrink-0 text-[10px]">▾</span>
      </button>
      <span className="invisible absolute left-0 top-7 z-20 w-64 whitespace-normal break-words rounded-md bg-slate-900 px-3 py-2 text-xs font-normal leading-5 text-white opacity-0 shadow-lg transition group-hover:visible group-hover:opacity-100 group-focus-within:visible group-focus-within:opacity-100">
        참가 지역: {region}
      </span>
    </span>
  );
}


function pageHref(filters: BidSearchParams, page: number) {
  const params = new URLSearchParams();

  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined && key !== "page") {
      params.set(key, value);
    }
  }

  params.set("page", String(page));
  return `/dashBoard/bidList?${params.toString()}`;
}


function filterHref(
  filters: BidSearchParams,
  key: "deadline_sort" | "notice_sort" | "contract_method",
  value: string,
) {
  const params = new URLSearchParams();

  for (const [filterKey, filterValue] of Object.entries(filters)) {
    if (filterValue !== undefined && filterKey !== "page") {
      params.set(filterKey, filterValue);
    }
  }

  if (value) params.set(key, value);
  else params.delete(key);

  return `/dashBoard/bidList${params.size ? `?${params}` : ""}`;
}

function getVisiblePages(currentPage: number, totalPages: number) {
  const visibleCount = Math.min(5, totalPages);
  const startPage = Math.max(
    1,
    Math.min(currentPage - 2, totalPages - visibleCount + 1),
  );

  return Array.from({ length: visibleCount }, (_, index) => startPage + index);
}

export default function BidTable({ data, error, filters }: BidTableProps) { // 입찰 데이터를 서버에서 가져오는 서버 컴포넌트
  const router = useRouter();
  const bids = data?.items ?? [];
  const visiblePages = data ? getVisiblePages(data.page, data.total_pages) : [];

  return (
    <section className="app-panel overflow-hidden rounded-lg border">
      {/* 검색 결과 제목과 공고 개수를 보여주는 영역 */}
      <div className="flex items-center justify-between border-b border-slate-200 bg-slate-50/60 px-5 py-3.5">
        <h2 className="text-sm font-semibold text-slate-800">
          검색 결과
        </h2>

        <p className="text-xs tabular-nums text-slate-500">
          총 {(data?.count ?? 0).toLocaleString("ko-KR")}건
        </p>
      </div>

      {/* 화면이 좁을 때 표를 가로로 스크롤할 수 있게 하는 영역 */}
      <div className="overflow-x-auto">
        <table className="w-full min-w-[1000px] border-collapse text-left text-sm">
          <thead className="bg-slate-50 text-slate-600">
            <tr>
              <th className="w-24 whitespace-nowrap px-3 py-3 font-semibold" scope="col">
                구분
              </th>

              <th className="min-w-[440px] px-4 py-3 text-center font-semibold" scope="col">
                공고명
              </th>

              <th className="w-36 whitespace-nowrap px-4 py-3 font-semibold" scope="col">
                <label className={`relative inline-flex cursor-pointer items-center gap-1 ${filters.contract_method ? "text-blue-600" : ""}`}>
                  <span>공고기관</span>
                  <span aria-hidden="true" className="text-xs">▾</span>
                  <select
                    aria-label="계약방법 필터"
                    className="absolute inset-0 h-full w-full cursor-pointer opacity-0"
                    onChange={(event) => router.push(filterHref(filters, "contract_method", event.target.value))}
                    value={filters.contract_method ?? ""}
                  >
                    <option value="">전체</option>
                    <option value="제한경쟁">제한경쟁</option>
                    <option value="수의계약">수의계약</option>
                    <option value="일반경쟁">일반경쟁</option>
                  </select>
                </label>
              </th>

              <th className="w-32 whitespace-nowrap px-4 py-3 font-semibold" scope="col">
                <span title="배정예산을 우선 표시하고, 없으면 추정가격을 표시합니다.">예산/추정가격</span>
              </th>

              <th className="w-28 whitespace-nowrap px-4 py-3 font-semibold" scope="col">
                <label className={`relative inline-flex cursor-pointer items-center gap-1 ${filters.notice_sort ? "text-blue-600" : ""}`}>
                  <span>공고일</span>
                  <span aria-hidden="true" className="text-xs">▾</span>
                  <select
                    aria-label="공고일 정렬"
                    className="absolute inset-0 h-full w-full cursor-pointer opacity-0"
                    onChange={(event) => router.push(filterHref(filters, "notice_sort", event.target.value))}
                    value={filters.notice_sort ?? ""}
                  >
                    <option value="">기본순</option>
                    <option value="asc">빠른순</option>
                    <option value="desc">느린순</option>
                  </select>
                </label>
              </th>

              <th className="w-28 whitespace-nowrap px-4 py-3 font-semibold" scope="col">
                <label className={`relative inline-flex cursor-pointer items-center gap-1 ${filters.deadline_sort ? "text-blue-600" : ""}`}>
                  <span>마감일</span>
                  <span aria-hidden="true" className="text-xs">▾</span>
                  <select
                    aria-label="마감일 정렬"
                    className="absolute inset-0 h-full w-full cursor-pointer opacity-0"
                    onChange={(event) => router.push(filterHref(filters, "deadline_sort", event.target.value))}
                    value={filters.deadline_sort ?? ""}
                  >
                    <option value="">기본순</option>
                    <option value="asc">빠른순</option>
                    <option value="desc">느린순</option>
                  </select>
                </label>
              </th>

              <th className="w-24 whitespace-nowrap px-4 py-3 text-center font-semibold" scope="col">
                작업
              </th>
            </tr>
          </thead>

          <tbody className="divide-y divide-slate-200">
            {error && (
              <tr>
                <td className="px-5 py-12 text-center text-slate-500" colSpan={7}>
                  {error}
                </td>
              </tr>
            )}

            {!error && bids.length === 0 && (
              <tr>
                <td className="px-5 py-12 text-center text-slate-500" colSpan={7}>
                  표시할 입찰공고가 없습니다.
                </td>
              </tr>
            )}

            {bids.map((bid) => ( // 입찰공고를 한 건씩 꺼내서 표의 행으로 반복 출력
              <tr
                key={`${bid.bidNtceNo}-${bid.bidNtceOrd}`} // 공고번호와 차수로 각 행을 구분
                className="hover:bg-slate-50"
              >
                <td className="px-3 py-4 text-slate-600">
                  {bid.bsnsDivNm} {/* 업무 구분 */}
                  <RegionInfo bid={bid} />
                </td>

                <td className="px-3 py-4">
                  <div className="leading-6">
                    <BidDetailModal
                      bid={bid}
                      flowTrigger
                      trigger={bid.bidNtceNm}
                      triggerClassName="inline cursor-pointer break-keep text-left font-semibold text-slate-950 transition-colors hover:text-blue-600 hover:underline"
                    /> {/* 공고명을 누르면 상세 팝업 열기 */}

                    {typeof bid.bidNtceUrl === "string" && bid.bidNtceUrl && (
                      <>
                        {" "}
                        <a
                          className="inline-flex h-6 cursor-pointer items-center justify-center rounded-md border border-slate-300 px-2 align-middle text-[11px] font-semibold text-slate-600 hover:border-blue-400 hover:text-blue-600"
                          href={bid.bidNtceUrl}
                          rel="noreferrer"
                          target="_blank"
                        >
                          원문
                        </a>
                      </>
                    )}
                  </div>

                </td>

                <td className="max-w-36 px-4 py-4 text-slate-600">
                  <span className="line-clamp-2" title={formatNoticeOrganization(bid)}>
                    {formatNoticeOrganization(bid)}
                  </span>
                </td>

                <td className="whitespace-nowrap px-4 py-4 text-slate-600">
                  {formatBidAmount(bid, "-")} {/* 배정 예산이 없으면 추정 가격 표시 */}
                </td>

                <td className="whitespace-nowrap px-4 py-4 text-slate-600">
                  {formatNoticeDate(bid)} {/* 공고 날짜 */}
                </td>

                <td className="whitespace-nowrap px-4 py-4 text-slate-600">
                  {bid.deadlineStatus === "review" ? (
                    <span className="inline-flex rounded-md bg-amber-50 px-2 py-1 text-xs font-semibold text-amber-800 ring-1 ring-inset ring-amber-200">
                      마감일 확인 필요
                    </span>
                  ) : (
                    <>
                      <p>{getDeadlineParts(bid).date}</p>
                      {getDeadlineParts(bid).time && (
                        <p className="mt-1 text-xs text-slate-500">{getDeadlineParts(bid).time}</p>
                      )}
                    </>
                  )}
                </td>

                <td className="whitespace-nowrap px-4 py-4">
                  <div className="flex items-start justify-center">
                    <SaveBidButton bidNtceNo={bid.bidNtceNo} />
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {data && (
        <nav
          aria-label="입찰공고 페이지"
          className="flex flex-wrap items-center justify-center gap-1.5 border-t border-slate-200 px-5 py-4"
        >
          {data.page > 1 ? (
            <Link
              aria-label="첫 페이지"
              className="flex h-9 w-9 items-center justify-center rounded-md border border-slate-200 text-lg text-slate-500 transition-colors hover:border-blue-300 hover:bg-blue-50 hover:text-blue-600"
              href={pageHref(filters, 1)}
              prefetch={false}
              title="첫 페이지"
            >
              «
            </Link>
          ) : (
            <span aria-hidden="true" className="flex h-9 w-9 items-center justify-center rounded-md border border-slate-100 text-lg text-slate-300">
              «
            </span>
          )}

          {data.page > 1 ? (
            <Link
              aria-label="이전 페이지"
              className="flex h-9 w-9 items-center justify-center rounded-md border border-slate-200 text-lg text-slate-500 transition-colors hover:border-blue-300 hover:bg-blue-50 hover:text-blue-600"
              href={pageHref(filters, data.page - 1)}
              prefetch={false}
              title="이전 페이지"
            >
              ‹
            </Link>
          ) : (
            <span aria-hidden="true" className="flex h-9 w-9 items-center justify-center rounded-md border border-slate-100 text-lg text-slate-300">
              ‹
            </span>
          )}

          {visiblePages[0] > 1 && (
            <span className="flex h-9 w-6 items-center justify-center text-sm text-slate-400">…</span>
          )}

          {visiblePages.map((pageNumber) => (
            pageNumber === data.page ? (
              <span
                aria-current="page"
                className="flex h-9 min-w-9 items-center justify-center rounded-md bg-blue-600 px-2 text-sm font-semibold text-white"
                key={pageNumber}
              >
                {pageNumber}
              </span>
            ) : (
              <Link
                aria-label={`${pageNumber}페이지`}
                className="flex h-9 min-w-9 items-center justify-center rounded-md border border-slate-200 px-2 text-sm font-medium text-slate-600 transition-colors hover:border-blue-300 hover:bg-blue-50 hover:text-blue-600"
                href={pageHref(filters, pageNumber)}
                key={pageNumber}
                prefetch={false}
              >
                {pageNumber}
              </Link>
            )
          ))}

          {visiblePages[visiblePages.length - 1] < data.total_pages && (
            <span className="flex h-9 w-6 items-center justify-center text-sm text-slate-400">…</span>
          )}

          {data.page < data.total_pages ? (
            <Link
              aria-label="다음 페이지"
              className="flex h-9 w-9 items-center justify-center rounded-md border border-slate-200 text-lg text-slate-500 transition-colors hover:border-blue-300 hover:bg-blue-50 hover:text-blue-600"
              href={pageHref(filters, data.page + 1)}
              prefetch={false}
              title="다음 페이지"
            >
              ›
            </Link>
          ) : (
            <span aria-hidden="true" className="flex h-9 w-9 items-center justify-center rounded-md border border-slate-100 text-lg text-slate-300">
              ›
            </span>
          )}

          {data.page < data.total_pages ? (
            <Link
              aria-label="마지막 페이지"
              className="flex h-9 w-9 items-center justify-center rounded-md border border-slate-200 text-lg text-slate-500 transition-colors hover:border-blue-300 hover:bg-blue-50 hover:text-blue-600"
              href={pageHref(filters, data.total_pages)}
              prefetch={false}
              title="마지막 페이지"
            >
              »
            </Link>
          ) : (
            <span aria-hidden="true" className="flex h-9 w-9 items-center justify-center rounded-md border border-slate-100 text-lg text-slate-300">
              »
            </span>
          )}
        </nav>
      )}
    </section>
  );
}
