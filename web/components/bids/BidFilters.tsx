"use client"; // 회사 검색 조건과 버튼 상태를 브라우저에서 관리

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import BusinessTypeDropdown from "@/components/ui/BusinessTypeDropdown";
import RegionDropdown from "@/components/ui/RegionDropdown";
import { parseRegions } from "@/components/ui/RegionSelector";
import { API_BASE_URL } from "@/lib/api";
import { getBidSyncState, startBidSync, subscribeBidSync } from "@/lib/bidSync";
import { getCompanyKeywords, parseKeywordText } from "@/lib/companyKeywords";
import type { BidSearchParams } from "@/types/bid";
import type { CompanyProfileData } from "@/types/company";

type BidFiltersProps = {
  filters: BidSearchParams;
  lastUpdatedAt: string;
};

export default function BidFilters({ filters, lastUpdatedAt }: BidFiltersProps) {
  const router = useRouter();
  const [query, setQuery] = useState(filters.q ?? "");
  const [businessType, setBusinessType] = useState(filters.business_type ?? "");
  const [keywords, setKeywords] = useState(() => parseKeywordText(filters.keywords));
  const [regions, setRegions] = useState(() => parseRegions(filters.regions ?? ""));
  const [savedKeywords, setSavedKeywords] = useState<string[]>([]); // 회사 정보에 저장된 원래 키워드
  const [savedRegions, setSavedRegions] = useState<string[]>([]); // 회사 정보에 저장된 원래 희망지역
  const [savedBusinessType, setSavedBusinessType] = useState(""); // 회사 정보에 저장된 공고 유형
  const [keywordInput, setKeywordInput] = useState("");
  const [syncState, setSyncState] = useState(getBidSyncState); // 페이지를 이동해도 유지되는 나라장터 업데이트 상태
  const [syncAuthError, setSyncAuthError] = useState("");

  useEffect(() => {
    const token = localStorage.getItem("auth_token");
    if (!token) return;

    async function loadCompanyConditions() {
      const response = await fetch(`${API_BASE_URL}/api/company-profile/`, {
        headers: { Authorization: `Token ${token}` },
      });
      if (!response.ok) return;

      const data = (await response.json()) as { profile: CompanyProfileData | null };
      if (!data.profile) return;

      const companyKeywords = getCompanyKeywords(data.profile);
      const companyRegions = parseRegions(data.profile.preferred_region);
      const companyBusinessType = {
        service: "용역",
        goods: "물품",
        construction: "공사",
      }[data.profile.preferred_bid_type] ?? "";
      const params = new URLSearchParams();

      setSavedKeywords(companyKeywords);
      setSavedRegions(companyRegions);
      setSavedBusinessType(companyBusinessType);

      if (
        filters.keywords !== undefined ||
        filters.regions !== undefined ||
        filters.business_type !== undefined
      ) return;

      setKeywords(companyKeywords);
      setRegions(companyRegions);
      setBusinessType(companyBusinessType);
      params.set("keywords", companyKeywords.join(","));
      params.set("regions", companyRegions.join(","));
      if (companyBusinessType) params.set("business_type", companyBusinessType);
      router.replace(`/dashBoard/bidList?${params}`); // 회사 조건으로 첫 검색 실행

    }

    loadCompanyConditions(); // 최초 진입 시 회사 정보의 검색 조건 불러오기
  }, [filters.business_type, filters.keywords, filters.regions, router]);

  useEffect(() => {
    let previousStatus = getBidSyncState().status;

    return subscribeBidSync((nextState) => {
      setSyncState(nextState);
      if (previousStatus === "syncing" && nextState.status === "success") {
        router.refresh();
      }
      previousStatus = nextState.status;
    });
  }, [router]);

  function addKeyword() {
    const keyword = keywordInput.trim();
    if (keyword && !keywords.includes(keyword)) setKeywords([...keywords, keyword]);
    setKeywordInput("");
  }

  function addRegion(region: string) {
    if (region === "__all__") {
      setRegions([]); // 전체 지역을 선택하면 기존 지역 조건을 모두 제거
      return;
    }

    if (region && !regions.includes(region)) {
      setRegions([...regions, region]); // 지역을 고르는 즉시 현재 검색 조건에 추가
    }
  }

  function loadSavedKeywords() {
    setQuery("");
    setKeywords(savedKeywords); // 회사 정보의 키워드를 현재 검색 조건에 복사
  }

  function loadSavedRegions() {
    setQuery("");
    setRegions(savedRegions); // 회사 정보의 희망지역을 현재 검색 조건에 복사
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const params = new URLSearchParams();

    if (query.trim()) {
      setKeywords([]);
      setRegions([]);
      params.set("q", query.trim());
      params.set("keywords", "");
      params.set("regions", ""); // 공고명을 입력하면 회사 조건을 제외하고 제목만 검색
    } else {
      params.set("keywords", keywords.join(","));
      params.set("regions", regions.join(","));
    }
    if (businessType) params.set("business_type", businessType);
    if (filters.deadline_sort) params.set("deadline_sort", filters.deadline_sort);
    if (filters.notice_sort) params.set("notice_sort", filters.notice_sort);
    if (filters.contract_method) params.set("contract_method", filters.contract_method);

    router.push(`/dashBoard/bidList${params.size ? `?${params}` : ""}`);
  }

  function resetFilters() {
    setQuery("");
    setBusinessType(savedBusinessType);
    setKeywords(savedKeywords);
    setRegions(savedRegions);
    setKeywordInput("");
    setSyncAuthError("");

    const params = new URLSearchParams({
      keywords: savedKeywords.join(","),
      regions: savedRegions.join(","),
    });
    if (savedBusinessType) params.set("business_type", savedBusinessType);

    router.push(`/dashBoard/bidList?${params}`); // 회사에 저장된 최초 조건으로 다시 조회
  }

  function refreshBidNotices() {
    const token = localStorage.getItem("auth_token");
    if (!token) {
      setSyncAuthError("로그인 후 공고를 업데이트할 수 있습니다.");
      return;
    }

    setSyncAuthError("");
    void startBidSync(token);
  }

  const isSyncing = syncState.status === "syncing";
  const syncError = syncAuthError || syncState.message;

  return (
    <form className="p-5 lg:p-6" onSubmit={handleSubmit}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-1.5">
          <p className="text-xs text-slate-500">마지막 업데이트: {lastUpdatedAt}</p>
          <button
            aria-label="나라장터 공고 새로고침"
            className="inline-flex h-7 w-7 cursor-pointer items-center justify-center rounded-md text-base text-slate-500 transition-colors hover:bg-slate-100 hover:text-blue-600 disabled:text-slate-300"
            disabled={isSyncing}
            onClick={refreshBidNotices}
            title="나라장터에서 최신 공고 불러오기"
            type="button"
          >
            <span className={isSyncing ? "animate-spin" : ""}>↻</span>
          </button>
        </div>
        <button className="cursor-pointer whitespace-nowrap text-xs font-semibold text-slate-500 transition-colors hover:text-slate-950" onClick={resetFilters} type="button">
          전체 초기화
        </button>
      </div>

      {syncError && <p className="mt-2 text-xs text-red-600">{syncError}</p>}

      <div className="mt-4 w-full space-y-4 lg:w-[70%]">
        <div className="grid gap-3 lg:grid-cols-2"> {/* 첫 줄: 회사에 저장된 검색 조건 */}
          <div className="min-w-0">
            <button className="mb-2 cursor-pointer text-xs font-semibold text-slate-500 transition-colors hover:text-slate-950 disabled:text-slate-300" disabled={savedKeywords.length === 0} onClick={loadSavedKeywords} type="button">
              저장된 키워드 불러오기
            </button>
            <div className="flex min-h-10 min-w-0 flex-wrap items-center gap-1.5 rounded-md border border-slate-300 px-2 py-1 focus-within:border-blue-500">
              {keywords.map((keyword) => (
                <span className="inline-flex h-7 shrink-0 items-center gap-1 rounded-md bg-blue-50 px-2 text-xs font-semibold text-blue-700" key={keyword}>
                  {keyword}
                  <button aria-label={`${keyword} 키워드 삭제`} className="cursor-pointer" onClick={() => setKeywords(keywords.filter((item) => item !== keyword))} type="button">×</button>
                </span>
              ))}
              <input
                className="ml-auto h-8 w-28 shrink-0 border-0 px-1 text-right text-sm outline-none"
                onChange={(event) => setKeywordInput(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") {
                    event.preventDefault();
                    addKeyword();
                  }
                }}
                placeholder="키워드 추가"
                value={keywordInput}
              />
              <button aria-label="검색 키워드 추가" className="h-7 w-7 shrink-0 cursor-pointer rounded-md text-lg text-slate-500 transition-colors hover:bg-slate-100" disabled={!keywordInput.trim()} onClick={addKeyword} title="검색 키워드 추가" type="button">+</button>
            </div>
          </div>

          <div className="min-w-0">
            <button className="mb-2 cursor-pointer text-xs font-semibold text-slate-500 transition-colors hover:text-slate-950 disabled:text-slate-300" disabled={savedRegions.length === 0} onClick={loadSavedRegions} type="button">
              저장된 희망지역 불러오기
            </button>
            <div className="flex min-h-10 min-w-0 flex-wrap items-center gap-1.5 rounded-md border border-slate-300 px-2 py-1 focus-within:border-blue-500">
              {regions.length === 0 && (
                <span className="inline-flex h-7 shrink-0 items-center rounded-md bg-emerald-50 px-2 text-xs font-semibold text-emerald-700">
                  전체 지역
                </span>
              )}
              {regions.map((region) => (
                <span className="inline-flex h-7 shrink-0 items-center gap-1 rounded-md bg-emerald-50 px-2 text-xs font-semibold text-emerald-700" key={region}>
                  {region}
                  <button aria-label={`${region} 지역 삭제`} className="cursor-pointer" onClick={() => setRegions(regions.filter((item) => item !== region))} type="button">×</button>
                </span>
              ))}
              <div className="ml-auto min-w-24 shrink-0">
                <RegionDropdown onSelect={addRegion} regions={regions} />
              </div>
            </div>
          </div>
        </div>

        <div className="grid items-end gap-3 lg:grid-cols-[minmax(0,1fr)_140px_72px]"> {/* 둘째 줄: 직접 검색 조건 */}
          <div className="min-w-0">
            <h2 className="mb-2 text-sm font-bold text-slate-950">나라장터 공고검색</h2>
            <input
              aria-label="공고명, 공고번호 또는 기관명 검색"
              className="h-10 w-full min-w-0 rounded-md border border-slate-300 px-3 text-sm outline-none focus:border-blue-500"
              onChange={(event) => setQuery(event.target.value)}
              placeholder="공고명, 공고번호, 기관명"
              type="search"
              value={query}
            />
          </div>

          <div className="min-w-0">
            <span className="mb-2 block text-sm font-bold text-slate-950">구분</span>
            <BusinessTypeDropdown onChange={setBusinessType} value={businessType} />
          </div>

          <button className="h-10 cursor-pointer rounded-md bg-slate-950 text-sm font-semibold text-white transition-colors hover:bg-blue-700" type="submit">검색</button>
        </div>
      </div>

    </form>
  );
}
