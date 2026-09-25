"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import PageHeader from "@/components/layout/PageHeader";
import TemplateGallery from "@/components/proposal/TemplateGallery";
import { API_BASE_URL } from "@/lib/api";
import type { ProposalTemplateOption } from "@/types/bid";

export default function TemplatesPage() {
  const [templates,setTemplates]=useState<ProposalTemplateOption[]>([]);
  const [selected,setSelected]=useState("");
  const [error,setError]=useState("");
  const [message,setMessage]=useState("");
  useEffect(()=>{
    const controller=new AbortController();
    async function load() {
      try {
        const token=localStorage.getItem("auth_token");
        if(!token) throw new Error("로그인 후 양식을 확인할 수 있습니다.");
        const response=await fetch(`${API_BASE_URL}/api/proposal-templates/`,{headers:{Authorization:`Token ${token}`},signal:controller.signal});
        if(!response.ok) throw new Error("양식 목록을 불러오지 못했습니다. 로그인 상태를 확인해 주세요.");
        const data=await response.json() as {templates:ProposalTemplateOption[]};
        setTemplates(data.templates); setSelected(localStorage.getItem("bid3_preferred_template")||"");
      } catch(cause) { if(!controller.signal.aborted) setError(cause instanceof Error?cause.message:"불러오기 오류"); }
    }
    void load(); return ()=>controller.abort();
  },[]);
  return <>
    <PageHeader title="PPT 양식 라이브러리" description="공공 제안부터 교육, 기술, 문화 사업까지 용도에 맞는 디자인을 살펴보세요." />
    <div className="mt-6 rounded-xl border border-slate-200 bg-white p-6 sm:p-8">
      <p className="mb-5 text-sm leading-6 text-slate-600">{templates.length ? `${templates.length}종의 양식을 준비했습니다. `:""}미리보기에서 페이지를 넘겨 보거나 편집 가능한 PPTX를 다운로드할 수 있습니다.</p>
      {error ? <p role="alert" className="text-sm text-red-600">{error} <Link href="/login" className="underline">로그인</Link></p>
        : templates.length ? <TemplateGallery templates={templates} selectedTemplateId={selected} recommendedTemplateId="" recommendationReason="" onSelect={(id)=>{
          setSelected(id); localStorage.setItem("bid3_preferred_template",id); setMessage("이 브라우저에서 새 제안서에 사용할 기본 양식으로 저장했습니다. 공고별로 다시 변경할 수 있습니다.");
        }}/>:<p className="text-sm text-slate-500">양식을 불러오는 중입니다.</p>}
      {message&&<p role="status" className="mt-4 text-sm text-emerald-700">{message}</p>}
      <Link href="/dashBoard/matchBid" className="mt-6 inline-flex text-sm font-semibold text-blue-700 hover:underline">제안서 제작으로 이동 →</Link>
    </div>
  </>;
}
