import BidChatWindow from "@/components/chat/BidChatWindow";

type PageProps = {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

export default async function BidChatPage({ searchParams }: PageProps) {
  const values = await searchParams;
  const bid = Array.isArray(values.bid) ? values.bid[0] : values.bid;
  const title = Array.isArray(values.title) ? values.title[0] : values.title;

  if (!bid) {
    return <p className="p-6 text-sm text-red-600">공고번호가 없어 채팅을 시작할 수 없습니다.</p>;
  }

  return <BidChatWindow bidNtceNo={bid} bidTitle={title || bid} />;
}
