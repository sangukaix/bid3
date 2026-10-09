"use client";
import type {BidProposalData} from "@/types/bid";

export default function ProposalFinalReviewPanel({plan,busy,disabled,onReview,onPage}:{
  plan:BidProposalData['revision_plan'];busy:boolean;disabled:boolean;onReview:()=>void;onPage:(n:number)=>void}) {
  const review=plan.final_document_review;
  return <section className="mt-4 rounded-md border border-slate-200 bg-white p-4">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <h3 className="font-semibold text-slate-900">최종 문서 전체 AI 검수</h3>
      <button type="button" disabled={busy || disabled} onClick={onReview} className="cursor-pointer rounded border border-blue-200 px-3 py-2 text-xs font-semibold text-blue-700 disabled:opacity-40">{busy ? "전체 문서 검수 중…" : "현재 파일 전체 AI 검수"}</button>
    </div>
    <p className="mt-2 text-xs leading-5 text-slate-500">선택한 모델로 모든 페이지의 회사 주장과 수치·일정 모순을 다시 검수합니다. 이 버튼은 파일을 수정하지 않으며 페이지 수에 따라 시간이 걸립니다.</p>
    {!review ? <p className="mt-3 text-sm text-slate-600">전체 AI 검수 기록이 없습니다.</p> : <>
      {review.stale ? <p className="mt-3 rounded bg-amber-50 p-3 text-sm text-amber-900">검수 이후 파일이나 회사 근거가 변경되었습니다. 저장된 검수 결과를 현재 파일의 확인 결과로 사용하지 마세요. 전체 AI 검수를 다시 실행해 주세요.</p> :
        <p className="mt-3 text-sm text-slate-700">{review.actual_slide_count}쪽 · 텍스트 {review.reviewed_block_count}개 검토 · 확인 필요 {review.review_required_count}건</p>}
      {!!review.failures.length && <details className="mt-3 text-xs text-amber-900"><summary className="cursor-pointer">자동 검수 실패 {review.failures.length}건</summary>{review.failures.map((text,i)=><p key={i}>{text}</p>)}</details>}
      {review.conflicts.map((item,i)=><article key={i} className="mt-3 rounded border border-amber-200 bg-amber-50 p-3 text-xs leading-5 text-amber-950">
        <p className="font-semibold">문서 내 조건 모순 후보</p><p>{item.reason}</p>
        <blockquote className="mt-2">{item.first_page}쪽: {item.first_quote}</blockquote>
        <blockquote className="mt-2">{item.second_page}쪽: {item.second_quote}</blockquote>
        {!review.stale && <div className="mt-2 flex gap-2">{[...new Set([item.first_page,item.second_page])].map(n=><button key={n} type="button" onClick={()=>onPage(n)} className="cursor-pointer rounded border border-amber-300 bg-white px-2 py-1">{n}쪽 확인</button>)}</div>}
      </article>)}
      <p className="mt-3 text-xs leading-5 text-slate-500">{review.limitation}</p>
    </>}
    {plan.bounded_repair && <p className="mt-3 rounded bg-slate-50 p-3 text-xs leading-5 text-slate-700">자동 보완 {plan.bounded_repair.attempt_count}회 · {plan.bounded_repair.reason}</p>}
  </section>;
}
