"use client";
import { useState } from "react";
import type { BidProposalData, CompanyClaimReview } from "@/types/bid";
type Props = { plan: BidProposalData["revision_plan"]; disabled: boolean; onReviewPage: (page: number) => void };

function Items({ review, disabled, onReviewPage, historical = false }: {
  review: CompanyClaimReview; disabled: boolean; onReviewPage: Props["onReviewPage"]; historical?: boolean;
}) {
  const [onlyProblems, setOnlyProblems] = useState(true);
  const items = review.items.filter(item => !onlyProblems || item.status !== "source_matched");
  return <div>
    <label className="my-3 flex items-center gap-2 text-sm text-slate-700">
      <input type="checkbox" checked={onlyProblems} onChange={e => setOnlyProblems(e.target.checked)} />
      확인 필요한 문장만 보기
    </label>
    {!items.length && <p className="py-3 text-sm text-slate-500">표시할 확인 대상이 없습니다. 모든 문장의 정확성을 보장하는 결과는 아닙니다.</p>}
    {items.map((item, i) => <article key={i} className="border-t border-slate-200 py-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h4 className="font-semibold text-slate-900">{item.slide_number}페이지 · {item.status === "source_matched" ? "원문 연결" : "근거 확인 필요"}</h4>
        {!historical && <button type="button" disabled={disabled || item.slide_number < 1 || item.slide_number > 100}
          onClick={() => onReviewPage(item.slide_number)}
          className="rounded border border-blue-200 px-3 py-1.5 text-sm font-semibold text-blue-700 hover:bg-blue-50 disabled:opacity-40">이 페이지 수정</button>}
      </div>
      <div className="mt-3 grid min-w-0 gap-4 xl:grid-cols-2">
        <div className="min-w-0">
          <p className="text-xs font-semibold text-slate-500">작성된 문장</p>
          <p className="mt-2 whitespace-pre-wrap break-words text-sm leading-6">{item.claim}</p>
          <p className="mt-2 break-words text-sm leading-6 text-amber-800">{item.reason}</p>
        </div>
        <div className="min-w-0 rounded bg-slate-50 p-3">
          <p className="text-xs font-semibold text-slate-500">대조한 회사 자료</p>
          {item.evidence_quote && <blockquote className="mt-2 whitespace-pre-wrap break-words text-sm leading-6">
            {item.evidence_quote}<footer className="mt-1 text-xs text-slate-500">{item.evidence_source}</footer>
          </blockquote>}
          {item.reference_passages?.length ? item.reference_passages.map((passage, n) => <details key={n} className="mt-2 text-sm">
            <summary className="cursor-pointer text-slate-700">{passage.source}</summary>
            <p className="mt-2 max-h-64 overflow-y-auto whitespace-pre-wrap break-words leading-6">{passage.text}</p>
          </details>) : !item.evidence_quote && <p className="mt-2 text-sm text-slate-500">저장된 대조 자료가 없습니다. 이전 기록이거나 관련 자료를 찾지 못한 경우입니다.</p>}
        </div>
      </div>
    </article>)}
  </div>;
}
export default function CompanyClaimReviewPanel({ plan, disabled, onReviewPage }: Props) {
  const history = plan.feedback_history ?? [];
  const latest = history.length ? history[history.length - 1].company_claim_review : plan.company_claim_review;
  const past = [
    ...(history.length && plan.company_claim_review ? [{ label: "최초 생성 검사", review: plan.company_claim_review }] : []),
    ...history.slice(0, -1).flatMap((entry, i) => entry.company_claim_review ? [{ label: `${i + 1}번째 수정 검사`, review: entry.company_claim_review }] : []),
  ];
  return <section className="mt-6 border-t border-slate-200 pt-5" aria-label="회사 근거 검토">
    <h3 className="text-base font-bold text-slate-950">회사 근거 검토</h3>
    <p className="mt-1 text-xs leading-5 text-slate-500">
      {history.length ? "최근 수정한 문장의 검사입니다. 변경하지 않은 문장은 이전 기록을 확인하세요." : "생성 시 회사 주장 후보를 대조한 결과입니다."}
      {" "}원문 연결은 증빙의 진위나 입찰 자격을 보증하지 않습니다.
    </p>
    {latest ? <Items review={latest} disabled={disabled} onReviewPage={onReviewPage} /> : <p className="py-4 text-sm text-slate-500">이 버전에 저장된 근거 검사 결과가 없습니다.</p>}
    {past.length > 0 && <details className="mt-3 border-t border-slate-200 pt-3">
      <summary className="cursor-pointer text-sm font-semibold text-slate-600">이전 검사 기록 {past.length}건</summary>
      <p className="mt-2 text-xs text-slate-500">이전 문장과 페이지 번호는 현재 파일과 다를 수 있습니다.</p>
      {past.map((entry, i) => <details key={i} className="mt-3">
        <summary className="cursor-pointer text-sm">{entry.label}</summary>
        <Items review={entry.review} historical disabled onReviewPage={onReviewPage} />
      </details>)}
    </details>}
  </section>;
}
