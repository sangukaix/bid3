import BidAnalysisReport from "@/components/analysis/BidAnalysisReport";
import SavedBidBoard from "@/components/savedBids/SavedBidBoard";

import PageHeader from "@/components/layout/PageHeader";

type PageProps = {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

export default async function ProposalAnalysisPage({ searchParams }: PageProps) {
  const values = await searchParams;
  const bidValue = values.bid;
  const bidNtceNo = Array.isArray(bidValue) ? bidValue[0] : bidValue;

  return (
    <section className="min-w-0">
      <PageHeader title="입찰성공률 분석" />
      {bidNtceNo ? (
        <BidAnalysisReport
          backHref="/dashBoard/matchBid/analysis"
          bidNtceNo={bidNtceNo}
        />
      ) : (
        <SavedBidBoard workflow="analysis" />
      )}
    </section>
  );
}
