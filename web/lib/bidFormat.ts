import type { BidNotice } from "@/types/bid";

// 공고의 배정예산을 우선 사용하고, 없으면 추정가격을 표시합니다.
export function formatBidAmount(
  bid: BidNotice,
  fallback = "확인 필요",
) {
  const amount = Number(bid.asignBdgtAmt || bid.presmptPrce);
  return Number.isFinite(amount) && amount > 0
    ? `${amount.toLocaleString("ko-KR")}원`
    : fallback;
}
