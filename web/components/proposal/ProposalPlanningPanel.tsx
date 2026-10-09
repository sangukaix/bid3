"use client";
import type {ProposalWritingPlan} from "@/types/bid";
const channels:Record<string,string> = {body:"제안서 본문",form:"별도 서식",eligibility:"자격·증빙",price:"가격·입찰금액",manual:"담당자 분류 확인"};

export default function ProposalPlanningPanel({plan,onPage}:{plan?:ProposalWritingPlan;onPage:(n:number)=>void}) {
  if (!plan) return null;
  return <details className="mt-4 rounded-md border border-slate-200 bg-white p-4">
    <summary className="cursor-pointer font-semibold text-slate-900">평가항목별 작성 계획 · 제출 업무 {plan.items.length}개</summary>
    <p className="mt-2 text-xs leading-5 text-slate-500">수행안과 페이지 배분입니다. 별도 서식·자격증빙·가격 업무는 본문 작성으로 완료 처리되지 않습니다.</p>
    {plan.notes.map((note,i)=><p key={i} className="mt-1 text-xs leading-5 text-slate-500">{note}</p>)}
    <div className="mt-3 space-y-3">{plan.items.map(item=><article key={item.id} className="rounded border border-slate-200 p-3 text-xs leading-5">
      <p className="font-semibold text-slate-900">{item.id} · {channels[item.channel] ?? item.channel} {item.evaluation_points && `· ${item.evaluation_points}`}</p>
      <p className="mt-1 text-sm text-slate-800">{item.requirement}</p>
      <p className="mt-1 text-slate-500">{item.sources?.join(" · ")}</p>
      <dl className="mt-3 grid gap-x-3 gap-y-1 sm:grid-cols-[80px_1fr]">
        {[["수행 방법",item.method],["담당 역할",item.responsible],["일정",item.schedule],["산출물",item.deliverable],["검증 방법",item.verification]].map(([label,value])=><div key={label} className="contents"><dt className="font-medium text-slate-600">{label}</dt><dd className="whitespace-pre-wrap text-slate-800">{value}</dd></div>)}
      </dl>
      {item.evidence_ids.length>0 && <p className="mt-2 text-blue-700">대조할 검토 완료 근거 후보: {item.evidence_ids.join(", ")}</p>}
      {item.question && <p className="mt-2 rounded bg-amber-50 p-2 text-amber-900">확인할 사항: {item.question}</p>}
      <div className="mt-2 flex flex-wrap gap-2">{item.output_slide_numbers?.map(n=><button type="button" key={n} onClick={()=>onPage(n)} className="cursor-pointer rounded border px-2 py-1 text-blue-700">{n}쪽 보기</button>)}</div>
    </article>)}</div>
  </details>;
}
