"use client";

import { useEffect, useRef, useState } from "react";
import { API_BASE_URL } from "@/lib/api";
import type { CompanyDocumentData, CompanyEvidenceItem } from "@/types/company";

const statuses = {pending:"검토 대기", approved:"검토 완료", excluded:"사용 제외", expired:"유효기간 만료", changed:"원문·항목 재확인"};
type Listing = {items:CompanyEvidenceItem[]; counts:Record<string,number>; page:number; pages:number;
  categories:Array<{value:string;label:string}>};

async function api(path:string, options:RequestInit = {}) {
  const token = localStorage.getItem("auth_token");
  if (!token) throw new Error("로그인 후 회사 근거를 확인해 주세요.");
  const response = await fetch(`${API_BASE_URL}/api/${path}`, {...options,
    headers:{Authorization:`Token ${token}`, ...options.headers}});
  const data = await response.json();
  if (!response.ok) {
    const message = data.error ?? Object.values(data).flat().filter(value => typeof value === "string").join(" ");
    throw new Error(message || "회사 근거 요청을 처리하지 못했습니다.");
  }
  return data;
}

function EvidenceEditor({item, onSaved, onCancel}:{item:CompanyEvidenceItem; onSaved:()=>void; onCancel:()=>void}) {
  const [title,setTitle] = useState(item.title);
  const [content,setContent] = useState(item.content);
  const validUntilInput = useRef<HTMLInputElement>(null);
  const [note,setNote] = useState(item.review_note);
  const [confirmed,setConfirmed] = useState(false);
  const [busy,setBusy] = useState(false);
  const [error,setError] = useState("");

  async function save(status:CompanyEvidenceItem['review_status']) {
    setBusy(true);setError("");
    try {
      await api(`company-evidence/${item.id}/`, {method:"PATCH",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({review_status:status,title,content,valid_until:validUntilInput.current?.value || null,review_note:note,
          expected_updated_at:item.updated_at,confirm_source_review:confirmed})});
      onSaved();
    } catch (error) { setError(error instanceof Error ? error.message : "저장하지 못했습니다."); }
    finally { setBusy(false); }
  }

  return <div className="mt-4 space-y-3 rounded-md bg-slate-50 p-4">
    <label className="block text-xs font-medium text-slate-700">근거 제목
      <input value={title} maxLength={200} onChange={event=>setTitle(event.target.value)} className="mt-1 w-full rounded border border-slate-300 bg-white p-2 text-sm" /></label>
    <label className="block text-xs font-medium text-slate-700">제안서에서 사용할 사실
      <textarea value={content} maxLength={2000} rows={4} onChange={event=>setContent(event.target.value)} className="mt-1 w-full rounded border border-slate-300 bg-white p-2 text-sm" /></label>
    <div className="grid gap-3 sm:grid-cols-2">
      <label className="text-xs font-medium text-slate-700">유효기간 마지막 날 (선택)
        <input type="date" ref={validUntilInput} defaultValue={item.valid_until ?? ""} className="mt-1 block w-full rounded border border-slate-300 bg-white p-2 text-sm" /></label>
      <label className="text-xs font-medium text-slate-700">검토 메모 (선택)
        <input value={note} maxLength={500} onChange={event=>setNote(event.target.value)} className="mt-1 block w-full rounded border border-slate-300 bg-white p-2 text-sm" /></label>
    </div>
    <label className="flex items-start gap-2 text-xs leading-5 text-slate-700">
      <input type="checkbox" checked={confirmed} onChange={event=>setConfirmed(event.target.checked)} className="mt-1" />
      원문과 발췌를 확인했고, 위 내용이 현재 회사의 사실과 일치합니다.</label>
    {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
    <div className="flex flex-wrap gap-2 text-xs font-semibold">
      <button type="button" disabled={busy || !confirmed || !title.trim() || !content.trim()} onClick={()=>void save('approved')}
        className="cursor-pointer rounded bg-blue-600 px-3 py-2 text-white disabled:opacity-40">검토 완료로 저장</button>
      <button type="button" disabled={busy} onClick={()=>void save('pending')} className="cursor-pointer rounded border border-slate-300 px-3 py-2">검토 대기로 저장</button>
      <button type="button" disabled={busy} onClick={()=>void save('excluded')} className="cursor-pointer rounded border border-slate-300 px-3 py-2">사용 제외</button>
      <button type="button" disabled={busy} onClick={onCancel} className="cursor-pointer px-3 py-2 text-slate-500">닫기</button>
    </div>
  </div>;
}

export default function CompanyEvidenceLibrary({documents}:{documents:CompanyDocumentData[]}) {
  const [listing,setListing] = useState<Listing>({items:[],counts:{},page:1,pages:1,categories:[]});
  const [status,setStatus] = useState("");
  const [category,setCategory] = useState("");
  const [page,setPage] = useState(1);
  const [reload,setReload] = useState(0);
  const [loading,setLoading] = useState(true);
  const [message,setMessage] = useState("");
  const [selectedDocument,setSelectedDocument] = useState("");
  const [force,setForce] = useState(false);
  const [analyzing,setAnalyzing] = useState(false);
  const [editing,setEditing] = useState<number | null>(null);
  const documentIds = documents.map(document=>document.id).join(",");

  useEffect(()=> {
    let active = true;
    const query = new URLSearchParams({status,category,page:String(page)});
    api(`company-evidence/?${query}`).then(data=> { if (active) {setListing(data);setLoading(false);} })
      .catch(error=> {if (active) {setMessage(error.message);setLoading(false);}});
    return ()=> {active=false;};
  },[status,category,page,reload,documentIds]);

  async function analyze() {
    if (!selectedDocument) return;
    setAnalyzing(true);setMessage("");
    try {
      const data = await api(`company-documents/${selectedDocument}/knowledge/`, {method:"POST",
        headers:{"Content-Type":"application/json"},body:JSON.stringify({force})});
      setMessage(data.reused ? "기존 추출 항목을 불러왔습니다. 원문과 함께 검토해 주세요." : `${data.item_count}개 항목을 추출했습니다. 아직 검토 대기 상태입니다.`);
      setEditing(null);setReload(value=>value+1);
    } catch (error) {setMessage(error instanceof Error ? error.message : "분석하지 못했습니다.");}
    finally {setAnalyzing(false);}
  }

  async function download(item:CompanyEvidenceItem) {
    try {
      const token = localStorage.getItem("auth_token");
      if (!token) throw new Error("로그인 후 원문을 확인해 주세요.");
      const response = await fetch(`${API_BASE_URL}/api/company-documents/${item.source_document_id}/download/`,
        {headers:{Authorization:`Token ${token}`}});
      if (!response.ok) throw new Error("원문을 내려받지 못했습니다.");
      const url = URL.createObjectURL(await response.blob());
      const link = document.createElement('a');link.href=url;link.download=item.source_name;link.click();
      setTimeout(()=>URL.revokeObjectURL(url),1000);
    } catch (error) {setMessage(error instanceof Error ? error.message : "원문을 확인하지 못했습니다.");}
  }

  return <section className="app-panel overflow-hidden rounded-lg border">
    <div className="border-b border-slate-200 px-6 py-4">
      <h2 className="text-base font-bold text-slate-950">회사 근거 보관함</h2>
      <p className="mt-1 text-sm leading-6 text-slate-500">원문을 확인한 항목만 제안서의 검토 완료 근거로 사용합니다. 만료되거나 원문이 바뀌면 재확인이 필요합니다.</p>
      <p className="mt-2 text-xs text-slate-600">검토 완료 {listing.counts.approved ?? 0} · 검토 대기 {listing.counts.pending ?? 0} · 재확인 {(listing.counts.expired ?? 0)+(listing.counts.changed ?? 0)} · 사용 제외 {listing.counts.excluded ?? 0}</p>
    </div>
    <div className="space-y-3 border-b border-slate-200 bg-slate-50/60 px-6 py-4">
      <div className="flex flex-wrap gap-2">
        <select aria-label="분석할 회사 문서" value={selectedDocument} onChange={event=>setSelectedDocument(event.target.value)} disabled={analyzing}
          className="min-w-0 flex-1 rounded border border-slate-300 bg-white p-2 text-sm">
          <option value="">분석할 회사 문서 선택</option>{documents.map(document=><option key={document.id} value={document.id}>{document.original_name}</option>)}</select>
        <button type="button" disabled={analyzing || !documents.some(document=>String(document.id)===selectedDocument)} onClick={()=>void analyze()}
          className="cursor-pointer rounded bg-blue-600 px-4 py-2 text-xs font-semibold text-white disabled:opacity-40">{analyzing ? "근거 추출 중…" : "근거 항목 추출"}</button>
      </div>
      <label className="flex items-start gap-2 text-xs leading-5 text-slate-600"><input type="checkbox" checked={force} disabled={analyzing}
        onChange={event=>setForce(event.target.checked)} className="mt-1" />다시 분석합니다. 해당 문서의 기존 항목과 검토 기록을 새 추출 결과로 대체합니다.</label>
      {analyzing && <p className="text-xs text-slate-500">문서 길이에 따라 시간이 걸릴 수 있습니다. 추출 후 각 항목의 원문을 확인해 주세요.</p>}
    </div>
    <div className="flex flex-wrap gap-2 px-6 py-4">
      <select aria-label="근거 검토 상태" value={status} onChange={event=>{setStatus(event.target.value);setPage(1);setEditing(null);}} className="rounded border border-slate-300 bg-white p-2 text-xs">
        <option value="">전체 상태</option>{Object.entries(statuses).map(([value,label])=><option key={value} value={value}>{label}</option>)}</select>
      <select aria-label="근거 분류" value={category} onChange={event=>{setCategory(event.target.value);setPage(1);setEditing(null);}} className="rounded border border-slate-300 bg-white p-2 text-xs">
        <option value="">전체 분류</option>{listing.categories.map(item=><option key={item.value} value={item.value}>{item.label}</option>)}</select>
      <button type="button" onClick={()=>{setEditing(null);setReload(value=>value+1);}} className="cursor-pointer px-2 text-xs font-semibold text-blue-700">새로고침</button>
    </div>
    {message && <p role="status" className="px-6 pb-4 text-sm text-slate-700">{message}</p>}
    {loading ? <p className="px-6 pb-6 text-sm text-slate-500">근거 목록을 불러오는 중입니다.</p> : listing.items.length===0 ?
      <p className="px-6 pb-6 text-sm text-slate-500">해당하는 근거 항목이 없습니다. 회사 자료를 등록하고 근거 항목을 추출해 주세요.</p> :
      <div className="divide-y divide-slate-200">{listing.items.map(item=><article key={item.id} className="px-6 py-5">
        <div className="flex items-start justify-between gap-3">
          <div><p className="text-xs text-slate-500">{item.category_label} · K{item.id}</p><h3 className="mt-1 text-sm font-semibold text-slate-900">{item.title}</h3></div>
          <span className={`shrink-0 rounded px-2 py-1 text-xs ${item.effective_status==='approved' ? 'bg-blue-50 text-blue-700' : 'bg-amber-50 text-amber-800'}`}>{statuses[item.effective_status]}</span>
        </div>
        <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-700">{item.content}</p>
        <p className="mt-2 break-words text-xs text-slate-500">{item.source_name} · {item.source_locations.join(", ")}</p>
        <details className="mt-3 rounded border border-slate-200 p-3 text-xs">
          <summary className="cursor-pointer font-medium text-slate-700">원문 발췌 확인</summary>
          <p className="mt-2 whitespace-pre-wrap leading-6 text-slate-600">{item.evidence_excerpt || "저장된 발췌가 없습니다. 자료를 다시 분석해 주세요."}</p>
        </details>
        {item.reviewed_at && <p className="mt-2 text-xs text-slate-500">검토자 {item.reviewed_by} · {new Date(item.reviewed_at).toLocaleDateString('ko-KR')} · 유효기간 {item.valid_until ?? '별도 지정 없음'}</p>}
        {item.review_note && <p className="mt-1 whitespace-pre-wrap text-xs text-slate-600">메모: {item.review_note}</p>}
        {item.effective_status==='changed' && <p className="mt-2 text-xs text-amber-800">검토한 내용과 원문 상태가 달라졌거나 원문을 읽지 못했습니다. 원문을 다시 확인해 주세요.</p>}
        <div className="mt-3 flex flex-wrap gap-3 text-xs font-semibold text-blue-700">
          {item.source_document_id && <button type="button" onClick={()=>void download(item)} className="cursor-pointer">원문 다운로드</button>}
          {item.source_url && <a href={item.source_url} target="_blank" rel="noreferrer">출처 웹페이지</a>}
          <button type="button" disabled={analyzing} onClick={()=>setEditing(item.id)} className="cursor-pointer disabled:opacity-40">항목 검토·수정</button>
        </div>
        {editing===item.id && <EvidenceEditor key={`${item.id}:${item.updated_at}`} item={item}
          onSaved={()=>{setEditing(null);setMessage("검토 내용을 저장했습니다.");setReload(value=>value+1);}} onCancel={()=>setEditing(null)} />}
      </article>)}</div>}
    {listing.pages>1 && <div className="flex justify-center gap-4 border-t border-slate-200 p-4 text-xs">
      <button type="button" disabled={listing.page<=1} onClick={()=>{setPage(listing.page-1);setEditing(null);}} className="cursor-pointer disabled:opacity-40">이전</button>
      <span>{listing.page} / {listing.pages}</span>
      <button type="button" disabled={listing.page>=listing.pages} onClick={()=>{setPage(listing.page+1);setEditing(null);}} className="cursor-pointer disabled:opacity-40">다음</button>
    </div>}
    <p className="border-t border-slate-200 px-6 py-3 text-xs leading-5 text-slate-500">검토 완료는 담당자가 자료를 확인했다는 기록입니다. 증빙 진위나 개별 입찰의 참가 자격 판정을 대신하지 않습니다. 스캔 PDF는 텍스트 인식이 필요할 수 있습니다.</p>
  </section>;
}
