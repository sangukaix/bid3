"use client";
import {useEffect,useState} from "react";
import {API_BASE_URL} from "@/lib/api";

type Report = {
  file_sha256:string;checked_at:string;
  automatic_checks:Array<{id:string;title:string;status:"checked"|"attention"|"unchecked";detail:string}>;
  manual_checks:Array<{title:string;detail:string}>;
  separate_requirements:Array<{id:string;requirement:string;channel_label:string;sources?:string[]}>;
  limitation:string;
};

export default function ProposalSubmissionPanel({bidNtceNo,proposalUpdatedAt,busy}:{
  bidNtceNo:string;proposalUpdatedAt:string;busy:boolean}) {
  const [refresh,setRefresh]=useState(0);
  const key=`${bidNtceNo}:${proposalUpdatedAt}:${refresh}`;
  const [result,setResult]=useState<{key:string;report:Report|null;error:string}>({key:"",report:null,error:""});
  const report=result.key===key ? result.report : null;
  const error=result.key===key ? result.error : "";
  const loading=result.key!==key;
  useEffect(()=>{
    if (busy) return;
    const token=localStorage.getItem("auth_token");if (!token) return;
    const controller=new AbortController();
    void fetch(`${API_BASE_URL}/api/bids/${bidNtceNo}/proposal/submission-check/`,{
      headers:{Authorization:`Token ${token}`},signal:controller.signal,
    }).then(async response=>{
      const data=await response.json();
      if (!response.ok) throw new Error(data.error ?? "제출 전 점검을 불러오지 못했습니다.");
      if (!controller.signal.aborted) setResult({key,report:data.report,error:""});
    }).catch(error=>{if (!controller.signal.aborted) setResult({key,report:null,error:error instanceof Error ? error.message : "점검 실패"});});
    return ()=>controller.abort();
  },[bidNtceNo,busy,key]);
  function download() {
    if (!report || busy) return;
    const url=URL.createObjectURL(new Blob([JSON.stringify(report,null,2)],{type:"application/json;charset=utf-8"}));
    const link=document.createElement("a");link.href=url;link.download=`proposal-review-${bidNtceNo}.json`;link.click();
    window.setTimeout(()=>URL.revokeObjectURL(url),1000);
  }
  const pending=report?.automatic_checks.filter(item=>item.status!=="checked").length ?? 0;
  return <section className="mt-4 rounded-md border border-slate-200 bg-white p-4" aria-label="제출 전 점검">
    <div className="flex flex-wrap items-center justify-between gap-3"><h3 className="font-semibold text-slate-900">제출 전 점검</h3>
      <div className="flex gap-2"><button type="button" disabled={busy || loading} onClick={()=>setRefresh(n=>n+1)} className="rounded border border-slate-200 px-3 py-2 text-xs text-blue-700 disabled:opacity-40">다시 점검</button>
        <button type="button" disabled={!report || busy || loading} onClick={download} className="rounded border border-slate-200 px-3 py-2 text-xs text-slate-600 disabled:opacity-40">검수 기록 내려받기</button></div>
    </div>
    <p className="mt-2 text-xs leading-5 text-slate-500">현재 PPTX를 읽는 코드 점검입니다. AI를 호출하거나 파일을 수정하지 않습니다.</p>
    {(busy || loading) && <p className="mt-3 text-sm text-slate-600" role="status">{busy ? "진행 중인 작업이 끝나면 다시 점검합니다." : "현재 파일 점검 중…"}</p>}
    {error && !busy && <p role="alert" className="mt-3 text-sm text-amber-900">{error}</p>}
    {report && !busy && <>
      <p className="mt-3 text-sm font-medium text-slate-800">자동 점검 {report.automatic_checks.length}항목 중 {pending}항목 확인 필요 · 담당자 확인 별도</p>
      <div className="mt-3 divide-y divide-slate-100">{report.automatic_checks.map(item=><details key={item.id} className="py-3">
        <summary className="flex cursor-pointer items-center justify-between gap-3 text-xs"><span className="font-medium text-slate-800">{item.title}</span><span className={item.status==="checked" ? "text-teal-700" : "text-amber-800"}>{item.status==="checked" ? "검사상 확인" : item.status==="unchecked" ? "미검수" : "확인 필요"}</span></summary><p className="mt-2 text-xs leading-5 text-slate-500">{item.detail}</p>
      </details>)}</div>
      <details className="mt-3 rounded bg-amber-50 p-3 text-xs text-amber-950" open><summary className="cursor-pointer font-semibold">담당자가 확인할 내용</summary>
        <ul className="mt-2 space-y-3">{report.manual_checks.map(item=><li key={item.title}><p className="font-medium">{item.title}</p><p className="mt-1 leading-5">{item.detail}</p></li>)}</ul>
      </details>
      {report.separate_requirements.length>0 && <details className="mt-3 text-xs"><summary className="cursor-pointer font-medium text-slate-700">별도 서식·증빙·가격·분류 확인 {report.separate_requirements.length}항목</summary><ul className="mt-2 max-h-72 space-y-3 overflow-y-auto">{report.separate_requirements.map(item=><li key={item.id} className="rounded bg-slate-50 p-3 leading-5"><p className="font-medium">{item.id} · {item.channel_label}</p><p className="mt-1">{item.requirement}</p><p className="mt-1 text-slate-500">{item.sources?.join(" · ")}</p></li>)}</ul></details>}
      <p className="mt-3 text-xs leading-5 text-slate-500">{report.limitation}</p>
    </>}
  </section>;
}
