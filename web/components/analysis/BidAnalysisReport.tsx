"use client"; // 저장된 분석 조회, AI 분석 실행, PDF 다운로드를 처리

import Link from "next/link";
import { useEffect, useState } from "react";

import BidDetailModal from "@/components/bids/BidDetailModal";
import { API_BASE_URL } from "@/lib/api";
import type { BidNotice } from "@/types/bid";

type EvaluationItem = {
  name: string;
  score: number;
  max_score: number;
  status: "충족" | "회사정보 보완 필요" | "공고문 확인 필요" | "확인 필요" | "미충족";
  explanation: string;
  source_numbers: number[];
};

type AnalysisSource = {
  number: number;
  file_name: string;
  location: string;
};

type AnalysisReport = {
  summary: string;
  fit_score: number;
  recommendation: string;
  overview: {
    ordering_organization: string;
    budget: string;
    bid_deadline: string;
    contract_period: string;
    project_summary: string;
  };
  evaluation_items: EvaluationItem[];
  eligibility: string[];
  required_documents: string[];
  technical_evaluation: string[];
  price_evaluation: string[];
  main_tasks: string[];
  required_staff: string[];
  certifications_and_experience: string[];
  contract_cautions: string[];
  strengths: string[];
  risks: string[];
  company_checks: string[];
  action_strategy: string[];
  sources: AnalysisSource[];
};

type AnalysisApiResponse = {
  report: AnalysisReport | null;
  updated_at: string | null;
  error?: string;
};

function ListSection({ items, title }: { items: string[]; title: string }) {
  return (
    <section className="border-b border-slate-200 px-5 py-6 last:border-b-0">
      <h3 className="text-sm font-bold text-slate-950">{title}</h3>
      <ul className="mt-3 space-y-2 text-sm leading-6 text-slate-600">
        {(items.length ? items : ["확인 필요"]).map((item, index) => <li key={`${title}-${index}`}>• {item}</li>)}
      </ul>
    </section>
  );
}

function statusColor(status: EvaluationItem["status"]) {
  if (status === "충족") return "bg-emerald-500";
  if (status === "미충족") return "bg-red-500";
  return "bg-amber-500";
}

function statusLabel(item: EvaluationItem) {
  if (item.status !== "확인 필요") return item.status;
  return item.explanation.includes("미입력")
    ? "회사정보 보완 필요"
    : "공고문 확인 필요";
}

export default function BidAnalysisReport({
  bidNtceNo,
  backHref = "/dashBoard/matchBid/analysis",
}: {
  bidNtceNo: string;
  backHref?: string;
}) {
  const [bid, setBid] = useState<BidNotice | null>(null);
  const [report, setReport] = useState<AnalysisReport | null>(null);
  const [updatedAt, setUpdatedAt] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadData() {
      const token = localStorage.getItem("auth_token");
      if (!token) {
        setError("로그인 후 확인이 가능합니다.");
        setIsLoading(false);
        return;
      }

      try {
        const [bidResponse, analysisResponse] = await Promise.all([
          fetch(`${API_BASE_URL}/api/bids/${bidNtceNo}/`),
          fetch(`${API_BASE_URL}/api/bids/${bidNtceNo}/analysis/`, {
            headers: { Authorization: `Token ${token}` },
          }),
        ]);
        if (!bidResponse.ok || !analysisResponse.ok) throw new Error();

        const bidData = (await bidResponse.json()) as { item: BidNotice };
        const analysisData = (await analysisResponse.json()) as AnalysisApiResponse;
        setBid(bidData.item);
        setReport(analysisData.report);
        setUpdatedAt(analysisData.updated_at);
      } catch {
        setError("공고 또는 분석 정보를 불러오지 못했습니다. Django 서버를 확인해 주세요.");
      } finally {
        setIsLoading(false);
      }
    }

    loadData();
  }, [bidNtceNo]);

  async function runAnalysis() {
    if (!window.confirm("공고 문서 전체와 회사 정보를 이용해 AI 분석을 시작합니다. 계속할까요?")) return;
    const token = localStorage.getItem("auth_token");
    if (!token) return;

    setIsAnalyzing(true);
    setError("");
    try {
      const response = await fetch(`${API_BASE_URL}/api/bids/${bidNtceNo}/analysis/`, {
        method: "POST",
        headers: { Authorization: `Token ${token}` },
      });
      const data = (await response.json()) as AnalysisApiResponse;
      if (!response.ok || !data.report) throw new Error(data.error || "AI 분석에 실패했습니다.");
      setReport(data.report);
      setUpdatedAt(data.updated_at);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "AI 분석에 실패했습니다.");
    } finally {
      setIsAnalyzing(false);
    }
  }

  async function downloadPdf() {
    const token = localStorage.getItem("auth_token");
    if (!token) return;
    const response = await fetch(`${API_BASE_URL}/api/bids/${bidNtceNo}/analysis/pdf/`, {
      headers: { Authorization: `Token ${token}` },
    });
    if (!response.ok) {
      setError("PDF를 만들지 못했습니다.");
      return;
    }

    const url = URL.createObjectURL(await response.blob());
    const link = document.createElement("a");
    link.href = url;
    link.download = `bid-analysis-${bidNtceNo}.pdf`;
    link.click();
    URL.revokeObjectURL(url);
  }

  if (isLoading) return <p className="mt-6 py-12 text-center text-sm text-slate-500">분석 정보를 불러오는 중입니다.</p>;
  if (!bid) return <p className="mt-6 rounded-md bg-red-50 p-5 text-sm text-red-600">{error || "공고를 찾지 못했습니다."}</p>;

  return (
    <div className="mt-6 space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <Link className="text-sm font-semibold text-blue-600 hover:text-blue-700" href={backHref}>← 성공률 분석</Link>
          <h2 className="mt-3 max-w-4xl text-xl font-bold leading-8 text-slate-950">{bid.bidNtceNm}</h2>
          <p className="mt-1 text-sm text-slate-500">{bid.bidNtceNo} · {bid.bsnsDivNm || "구분 확인 필요"}</p>
        </div>
        <div className="flex gap-2">
          <BidDetailModal bid={bid} />
          {typeof bid.bidNtceUrl === "string" && bid.bidNtceUrl ? <a className="rounded-md border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-700 hover:border-blue-400 hover:text-blue-600" href={bid.bidNtceUrl} rel="noreferrer" target="_blank">나라장터 원문</a> : null}
        </div>
      </div>

      {error && <p className="rounded-md bg-red-50 px-4 py-3 text-sm text-red-600">{error}</p>}

      {!report ? (
        <section className="rounded-lg border border-blue-200 bg-blue-50 px-6 py-10 text-center">
          <h3 className="text-lg font-bold text-blue-950">성공률 분석</h3>
          <p className="mx-auto mt-2 max-w-2xl text-sm leading-6 text-blue-800">공고 문서와 회사 정보를 비교해 참가 가능성과 준비 사항을 진단합니다. 결과 점수는 낙찰 확률 예측이 아니라 공고 적합도입니다.</p>
          <button className="mt-6 rounded-md bg-blue-600 px-5 py-3 text-sm font-semibold text-white hover:bg-blue-700 disabled:bg-blue-300" disabled={isAnalyzing} onClick={runAnalysis} type="button">
            {isAnalyzing ? "문서를 확인하고 분석하는 중..." : "AI 분석 시작"}
          </button>
          <p className="mt-3 text-xs text-blue-700">최초 분석에만 크레딧이 소모되며, 결과는 저장되어 언제든지 열람할 수 있습니다.</p>
        </section>
      ) : (
        <>
          <section className="rounded-lg border border-slate-200 bg-white">
            <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 px-5 py-5">
              <div>
                <p className="text-xs font-semibold text-blue-600">공고 적합도</p>
                <div className="mt-1 flex items-end gap-3"><strong className="text-3xl text-slate-950">{report.fit_score}점</strong><span className="pb-1 text-sm font-semibold text-slate-600">{report.recommendation}</span></div>
              </div>
              <div className="flex items-center gap-3">
                {updatedAt && <span className="text-xs text-slate-500">저장 {new Date(updatedAt).toLocaleDateString("ko-KR")}</span>}
                <button className="rounded-md border border-blue-200 px-4 py-2 text-xs font-semibold text-blue-700 hover:bg-blue-50" onClick={downloadPdf} type="button">보고서 내려받기</button>
              </div>
            </div>
            <div className="px-5 py-5"><h3 className="text-sm font-bold text-slate-950">분석 요약</h3><p className="mt-2 text-sm leading-7 text-slate-600">{report.summary}</p></div>
          </section>

          <div className="grid gap-5 lg:grid-cols-2">
            <section className="rounded-lg border border-emerald-200 bg-emerald-50"><ListSection items={report.strengths} title="우리 회사의 강점" /></section>
            <section className="rounded-lg border border-red-200 bg-red-50"><ListSection items={report.risks} title="위험 요소" /></section>
          </div>

          <section className="rounded-lg border border-slate-200 bg-white">
            <div className="border-b border-slate-200 px-5 py-4"><h3 className="font-bold text-slate-950">사업 개요</h3></div>
            <dl className="grid sm:grid-cols-2">
              {[["발주기관", report.overview.ordering_organization], ["예산/추정가격", report.overview.budget], ["입찰 마감", report.overview.bid_deadline], ["계약 기간", report.overview.contract_period]].map(([label, value]) => (
                <div className="border-b border-slate-100 px-5 py-4 sm:odd:border-r" key={label}><dt className="text-xs text-slate-500">{label}</dt><dd className="mt-1 text-sm font-semibold text-slate-800">{value}</dd></div>
              ))}
            </dl>
            <div className="px-5 py-4"><h4 className="text-xs text-slate-500">사업 내용</h4><p className="mt-2 text-sm leading-6 text-slate-700">{report.overview.project_summary}</p></div>
          </section>

          <section className="rounded-lg border border-slate-200 bg-white">
            <div className="border-b border-slate-200 px-5 py-4"><h3 className="font-bold text-slate-950">평가 항목</h3><p className="mt-1 text-xs text-slate-500">적합도는 낙찰 확률이 아니라 회사 조건과 공고 요건의 일치 정도입니다.</p></div>
            <div className="divide-y divide-slate-100">
              {report.evaluation_items.map((item) => {
                const percent = Math.min(100, Math.round((item.score / item.max_score) * 100));
                return (
                  <div className="px-5 py-5" key={item.name}>
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div className="flex items-center gap-2"><h4 className="text-sm font-semibold text-slate-800">{item.name}</h4><span className="rounded-md bg-slate-100 px-2 py-1 text-[11px] font-semibold text-slate-600">{statusLabel(item)}</span></div>
                      <span className="text-sm font-bold text-slate-700">{item.score}/{item.max_score}</span>
                    </div>
                    <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-100"><div className={`h-full ${statusColor(item.status)}`} style={{ width: `${percent}%` }} /></div>
                    <p className="mt-2 text-xs leading-5 text-slate-500">{item.explanation}</p>
                  </div>
                );
              })}
            </div>
          </section>

          <section className="overflow-hidden rounded-lg border border-slate-200 bg-white">
            <ListSection items={report.eligibility} title="참가 자격" />
            <ListSection items={report.required_documents} title="필수 제출 서류" />
            <ListSection items={report.technical_evaluation} title="기술평가 기준" />
            <ListSection items={report.price_evaluation} title="가격평가 기준" />
            <ListSection items={report.main_tasks} title="주요 과업" />
            <ListSection items={report.required_staff} title="요구 인력 및 자격" />
            <ListSection items={report.certifications_and_experience} title="필수 인증 및 실적" />
            <ListSection items={report.contract_cautions} title="계약상 주의사항" />
          </section>

          <section className="overflow-hidden rounded-lg border border-slate-200 bg-white">
            <ListSection items={report.company_checks} title="회사가 반드시 확인할 사항" />
            <ListSection items={report.action_strategy} title="참여 준비 전략" />
          </section>

          <section className="rounded-lg border border-slate-200 bg-white px-5 py-5">
            <h3 className="text-sm font-bold text-slate-950">문서 출처</h3>
            <ol className="mt-3 space-y-2 text-xs leading-5 text-slate-500">
              {report.sources.map((source) => <li key={`${source.number}-${source.file_name}-${source.location}`}>출처 {source.number}. {source.file_name} · {source.location}</li>)}
            </ol>
          </section>
        </>
      )}
    </div>
  );
}
