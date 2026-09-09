import RecommendedBidBoard from "@/components/recommendations/RecommendedBidBoard";

import PageHeader from "@/components/layout/PageHeader";

export default function RecommendedBidPage() {
  return (
    <section className="min-w-0">
      <PageHeader title="추천 공고" />
      <RecommendedBidBoard />
    </section>
  );
}
