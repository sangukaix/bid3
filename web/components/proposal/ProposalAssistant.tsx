"use client"; // 공고 질문과 제안서 수정을 하나의 AI비서 대화창으로 제공

import BidChatWindow from "@/components/chat/BidChatWindow";
import type { BidProposalData } from "@/types/bid";

type ProposalAssistantProps = {
  bidNtceNo: string;
  bidTitle: string;
  proposal: BidProposalData | null;
  disabled: boolean;
  selectedSlide?: number;
  onUpdated: (proposal: BidProposalData) => void;
};

export default function ProposalAssistant({
  bidNtceNo,
  bidTitle,
  proposal,
  disabled,
  selectedSlide,
  onUpdated,
}: ProposalAssistantProps) {
  return (
    <section className="flex h-full min-h-[620px] flex-col bg-white">
      <header className="border-b border-slate-200 px-4 py-4">
        <h2 className="text-base font-bold text-slate-950">AI비서</h2>
        <p className="mt-1 text-xs leading-5 text-slate-500">
          공고 질문과 제안서 수정 요청을 한 대화에서 진행할 수 있습니다.
        </p>
      </header>

      <div className="min-h-0 flex-1">
        <BidChatWindow
          bidNtceNo={bidNtceNo}
          bidTitle={bidTitle}
          embedded
          onProposalUpdated={onUpdated}
          selectedSlide={selectedSlide}
          showHeader={false}
        />
      </div>

      {(disabled || !proposal) && (
        <p className="border-t border-amber-100 bg-amber-50 px-4 py-2 text-xs text-amber-700">
          {!proposal
            ? "제안서 초안이 완성되기 전에는 공고 질문만 가능합니다."
            : "제안서 생성 중에는 수정 요청을 반영할 수 없습니다."}
        </p>
      )}
    </section>
  );
}
