import BidFilters from "@/components/bids/BidFilters"; // 입찰공고 검색 조건 영역
import BidSummary from "@/components/bids/BidSummary"; // 공고 유형별 개수 요약 영역
import BidTable from "@/components/bids/BidTable"; // 입찰공고 표 영역
import type { BidApiResponse, BidSearchParams } from "@/types/bid";

type BidListProps = {
  filters: BidSearchParams;
};

const emptySummary = {
  total: 0,
  goods: 0,
  services: 0,
  construction: 0,
};

function formatLastUpdatedAt(value: string | null | undefined) {
  if (!value) {
    return "아직 수집된 기록이 없습니다.";
  }

  return new Intl.DateTimeFormat("ko-KR", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "Asia/Seoul",
  }).format(new Date(value));
}

async function fetchBids(filters: BidSearchParams) {
  const apiBaseUrl = process.env.BID_API_BASE_URL ?? "http://127.0.0.1:8000";
  const params = new URLSearchParams({
    page: filters.page || "1",
    page_size: "20",
  });

  for (const [key, value] of Object.entries(filters)) {
    if (value && key !== "page") {
      params.set(key, value);
    }
  }

  try {
    const response = await fetch(`${apiBaseUrl}/api/bids/?${params}`, {
      cache: "no-store",
    });

    if (!response.ok) {
      throw new Error(`API response error: ${response.status}`);
    }

    return {
      data: (await response.json()) as BidApiResponse,
      error: null,
    };
  } catch {
    return {
      data: null,
      error: "입찰공고를 불러오지 못했습니다. Django 서버를 확인해 주세요.",
    };
  }
}

export default async function BidList({ filters }: BidListProps) { // 입찰 목록 화면에 필요한 컴포넌트를 순서대로 조립
  const { data, error } = await fetchBids(filters);

  return (
    <div className="mt-5 space-y-4">
      <div className="app-panel relative z-20 overflow-visible rounded-lg border">
        <BidSummary summary={data?.summary ?? emptySummary} />
        <BidFilters
          filters={filters}
          lastUpdatedAt={formatLastUpdatedAt(data?.last_updated_at)}
        />
      </div>
      <BidTable data={data} error={error} filters={filters} />
    </div>
  );
}
