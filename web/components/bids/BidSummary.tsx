import type { BidSummaryData } from "@/types/bid";

type BidSummaryProps = {
  summary: BidSummaryData;
};

export default function BidSummary({ summary }: BidSummaryProps) {
  const summaryItems = [
    { label: "전체 공고", count: summary.total },
    { label: "물품", count: summary.goods },
    { label: "용역", count: summary.services },
    { label: "공사", count: summary.construction },
  ];

  return (
    <section className="overflow-x-auto border-b border-slate-200 bg-slate-50/60" aria-label="입찰공고 요약">
      <div className="grid min-w-[560px] grid-cols-4 divide-x divide-slate-200">
        {summaryItems.map((item) => (
          <div className="flex items-center justify-between gap-3 px-5 py-3.5" key={item.label}>
            <p className="whitespace-nowrap text-xs font-medium text-slate-500">{item.label}</p>
            <p className="text-lg font-semibold tabular-nums text-slate-900">{item.count.toLocaleString()}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
