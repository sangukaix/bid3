import type { Quality } from "./api";

export default function QualityReview({ review }: { review?: Quality }) {
  if (!review?.pages?.length) return null;
  const pages = review.pages;
  const repaired = pages.filter(p => p.repaired_once).length;
  const findings = pages.flatMap(p => p.findings.map(f => ({ ...f, page: p.page })));
  return <details className="rounded-xl border border-violet-100 bg-white p-4" open={findings.length > 0}>
    <summary className="cursor-pointer text-sm font-semibold text-violet-900">작성 검수 · {pages.length}쪽 확인{repaired > 0 ? ` · ${repaired}쪽 보완` : ""}{findings.length > 0 ? ` · 확인할 내용 ${findings.length}개` : ""}</summary>
    <div className="mt-3 space-y-3 text-xs leading-5 text-slate-600">
      {pages.map((p, i) => <div key={`${p.page}-${i}`} className="border-t border-slate-100 pt-3">
        <p className="font-semibold text-slate-800">{p.page}쪽 · 텍스트 공간 확인{p.semantic_checked ? " · Gemma 내용 검수" : ""}{p.repaired_once ? " · 한 번 보완 후 재검수" : ""}</p>
        {p.repaired_once && p.initial_findings.map((f, j) => <p key={j} className="mt-1">보완 사유: {f.problem}</p>)}
        {p.findings.map((f, j) => <p key={j} className="mt-1 text-amber-800">Gemma 확인 제안: {f.problem}</p>)}
        {p.citations.filter((c, j, all) => all.findIndex(v => v.reference_id === c.reference_id && v.part === c.part) === j).map((c, j) => <p key={j} className="mt-1">내용 근거: {p.sources.find(s => s.id === c.reference_id)?.name || "참고자료"} · 발췌 {c.part}</p>)}
        {!!p.omitted_reference_count && <p className="mt-1 text-amber-800">입력 길이 제한으로 {p.omitted_reference_count}개 자료가 검수에서 제외되었습니다.</p>}
      </div>)}
      <p className="text-slate-500">텍스트 공간은 폰트와 상자 크기로 추정합니다. 아래 미리보기에서 최종 배치를 확인해 주세요.</p>
    </div>
  </details>;
}
