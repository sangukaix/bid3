import BidList from "@/components/bids/BidList"; // 입찰공고 목록 화면 전체를 조립하는 컴포넌트
import type { BidSearchParams } from "@/types/bid";

import PageHeader from "@/components/layout/PageHeader";

type PageProps = {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

function firstValue(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

export default async function BidListPage({ searchParams }: PageProps) { // /dashBoard/bidList 주소에서 보이는 페이지
  const values = await searchParams;
  const filters: BidSearchParams = {
    q: firstValue(values.q),
    keywords: firstValue(values.keywords),
    regions: firstValue(values.regions),
    business_type: firstValue(values.business_type),
    region: firstValue(values.region),
    deadline_days: firstValue(values.deadline_days),
    deadline_status: firstValue(values.deadline_status),
    deadline_sort: firstValue(values.deadline_sort) as "asc" | "desc" | undefined,
    notice_sort: firstValue(values.notice_sort) as "asc" | "desc" | undefined,
    contract_method: firstValue(values.contract_method) as BidSearchParams["contract_method"],
    page: firstValue(values.page),
  };

  return (
    <section className="min-w-0"> {/* 표가 넓어져도 대시보드 영역을 밀어내지 않도록 설정 */}
      <PageHeader title="입찰공고 목록" /> {/* 모든 페이지에서 같은 위치와 크기로 제목 표시 */}

      <BidList filters={filters} /> {/* 요약, 검색 필터, 표를 한 번에 표시 */}
    </section>
  );
}
