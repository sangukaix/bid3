"use client";
import { useState } from "react";
import type { ProposalOutputReview } from "@/types/bid";

type Props = { review?: ProposalOutputReview; disabled: boolean; refreshing: boolean;
  onRefresh: () => void; onPage: (page: number) => void };

export default function ProposalOutputReviewPanel({ review, disabled, refreshing, onRefresh, onPage }: Props) {
  const [onlyProblems, setOnlyProblems] = useState(true);
  const [visibleCount, setVisibleCount] = useState(30);
  const checks = (review?.checks ?? []).filter(item => !onlyProblems || !item.covered);
  return <section className="mt-4 rounded-md border border-slate-200 bg-white p-4">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <h3 className="font-semibold text-slate-900">공고 요구사항 · 최종 파일 대조</h3>
      <button type="button" disabled={disabled || refreshing} onClick={onRefresh}
        className="cursor-pointer rounded border border-blue-200 px-3 py-2 text-xs font-semibold text-blue-700 hover:bg-blue-50 disabled:opacity-40">
        {refreshing ? "대조 중…" : "최신 파일 대조"}
      </button>
    </div>
    <p className="mt-2 text-xs leading-5 text-slate-500">저장된 검수 인용을 현재 PPTX에서 확인합니다. 답변을 바꾸면 기존 확인 결과가 해제될 수 있습니다.</p>
    {!review ? <p className="mt-3 text-sm text-slate-600">이 파일에 저장된 대조 결과가 없습니다. 최신 파일 대조를 눌러 확인하세요.</p> : <>
      {review.source_register_available && <p className="mt-3 text-sm text-slate-700">
        출력 {review.actual_slide_count}쪽 · 요구사항 {review.total_count}개 · 본문 인용 확인 {review.matched_count}개 · 재검토 {review.review_required_count}개
      </p>}
      {review.review_notes.length > 0 && <ul className="mt-3 list-disc space-y-1 rounded bg-amber-50 p-3 pl-7 text-xs leading-5 text-amber-900">
        {review.review_notes.map((note, i) => <li key={i}>{note}</li>)}
      </ul>}
      {review.checks.length > 0 && <>
        <label className="my-3 flex items-center gap-2 text-xs text-slate-700">
          <input type="checkbox" checked={onlyProblems} onChange={event => { setOnlyProblems(event.target.checked); setVisibleCount(30); }} />
          재검토 항목만 보기
        </label>
        {checks.length === 0 && <p className="py-3 text-sm text-slate-600">재검토로 표시된 본문 항목이 없습니다. 별도 서식·증빙과 자격 요건은 직접 확인하세요.</p>}
        {checks.length > 0 && <div className="overflow-x-auto">
          <table className="w-full min-w-[700px] text-left text-xs leading-5">
            <thead className="bg-slate-50 text-slate-600"><tr>
              <th className="p-3">요구사항 · 평가항목</th><th className="p-3">공고 출처 · 서식</th><th className="p-3">현재 답변 · 확인 상태</th>
            </tr></thead>
            <tbody>{checks.slice(0, visibleCount).map(item => <tr key={item.id} className="border-t border-slate-200 align-top">
              <td className="w-2/5 p-3"><p className="font-medium text-slate-900">{item.requirement}</p>
                <p className="mt-1 text-slate-500">{[item.id, item.category, item.priority, item.evaluation_points].filter(Boolean).join(" · ")}</p></td>
              <td className="w-1/4 whitespace-pre-wrap p-3 text-slate-600">
                {item.sources?.length ? item.sources.join("\n") : "저장된 원문 위치 없음"}
                {item.form_name && <p className="mt-2 font-medium">서식: {item.form_name}</p>}</td>
              <td className="p-3"><p className={item.covered ? "font-medium text-blue-700" : "font-medium text-amber-800"}>
                {item.covered ? "본문 인용 확인" : "재검토 필요"}</p>
                {item.quote && <blockquote className="mt-2 whitespace-pre-wrap text-slate-700">{item.quote}</blockquote>}
                {item.reason && <p className="mt-2 text-slate-500">{item.reason}</p>}
                {item.slide_number && <button type="button" disabled={disabled} onClick={() => onPage(item.slide_number!)}
                  className="mt-2 cursor-pointer rounded border border-slate-200 px-2 py-1 text-blue-700">{item.slide_number}쪽 보기</button>}
              </td></tr>)}</tbody>
          </table>
        </div>}
        {checks.length > visibleCount && <button type="button" onClick={() => setVisibleCount(count => count + 30)}
          className="mt-3 cursor-pointer text-sm font-medium text-blue-700">다음 항목 더 보기 ({checks.length - visibleCount}개 남음)</button>}
      </>}
      {review.open_text_items.length > 0 && <details className="mt-4 text-xs">
        <summary className="cursor-pointer font-semibold text-amber-800">확인 필요·미작성 문구 {review.open_text_items.length}개</summary>
        {review.open_text_items.map((item, i) => <div key={i} className="mt-2 flex items-start gap-3 rounded bg-slate-50 p-2">
          <button type="button" disabled={disabled} onClick={() => onPage(item.slide_number)} className="shrink-0 cursor-pointer text-blue-700">{item.slide_number}쪽</button>
          <p className="whitespace-pre-wrap break-words text-slate-600">{item.text}</p>
        </div>)}
      </details>}
      <p className="mt-4 text-xs leading-5 text-slate-500">{review.limitation}</p>
    </>}
  </section>;
}
