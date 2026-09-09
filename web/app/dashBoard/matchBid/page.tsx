import SavedBidBoard from "@/components/savedBids/SavedBidBoard";

import PageHeader from "@/components/layout/PageHeader";

export default function MatchBidPage() {
  return (
    <section className="min-w-0">
      <PageHeader title="제안서 제작" />
      <SavedBidBoard workflow="proposal" />
    </section>
  );
}
