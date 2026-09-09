"use client"; // 프로젝트 안에서 저장된 분석을 조회하거나 최초 분석 실행

import Link from "next/link";
import { useEffect, useState } from "react";

import { API_BASE_URL } from "@/lib/api";

type AnalysisReport = {
  summary: string;
  fit_score: number;
  recommendation: string;
};

export default function ProjectAnalysisCard({ bidNtceNo }: { bidNtceNo: string }) {
  const [report, setReport] = useState<AnalysisReport | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const token = localStorage.getItem("auth_token");
    if (!token) return;

    void fetch(`${API_BASE_URL}/api/bids/${bidNtceNo}/analysis/`, {
      headers: { Authorization: `Token ${token}` },
    })
      .then((response) => response.json())
      .then((data: { report?: AnalysisReport | null }) => setReport(data.report ?? null))
      .catch(() => setError("저장된 분석을 불러오지 못했습니다."));
  }, [bidNtceNo]);

  async function runAnalysis() {
    const token = localStorage.getItem("auth_token");
    if (!token || isAnalyzing) return;
    if (!window.confirm("공고 문서와 회사 정보를 비교해 입찰성공률 분석을 시작할까요?")) return;

    setIsAnalyzing(true);
    setError("");
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/bids/${bidNtceNo}/analysis/`,
        { method: "POST", headers: { Authorization: `Token ${token}` } },
      );
      const data = (await response.json().catch(() => ({}))) as {
        report?: AnalysisReport;
        error?: string;
      };
      if (!response.ok || !data.report) {
        throw new Error(data.error || "분석을 완료하지 못했습니다.");
      }
      setReport(data.report);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "분석을 완료하지 못했습니다.");
    } finally {
      setIsAnalyzing(false);
    }
  }

  return (
    <section className="border-b border-slate-200 py-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-bold text-slate-950">입찰성공률 분석</h3>
          <p className="mt-1 text-xs text-slate-500">공고 조건과 회사 역량의 적합도를 분석합니다.</p>
        </div>
        {!report && (
          <button
            className="inline-flex cursor-pointer items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-slate-300"
            disabled={isAnalyzing}
            onClick={() => void runAnalysis()}
            type="button"
          >
            {isAnalyzing && <span className="h-4 w-4 animate-spin rounded-full border-2 border-blue-200 border-t-white" />}
            {isAnalyzing ? "분석 중..." : "제안서 분석하기"}
          </button>
        )}
      </div>

      {report && (
        <div className="mt-4 rounded-md border border-blue-100 bg-blue-50/60 p-4">
          <div className="flex items-center justify-between gap-3">
            <p className="text-sm font-semibold text-slate-800">{report.recommendation}</p>
            <strong className="text-2xl text-blue-700">{report.fit_score}점</strong>
          </div>
          <p className="mt-2 line-clamp-3 text-sm leading-6 text-slate-600">{report.summary}</p>
          <Link
            className="mt-3 inline-flex cursor-pointer text-sm font-semibold text-blue-700 hover:underline"
            href={`/dashBoard/matchBid/analysis?bid=${encodeURIComponent(bidNtceNo)}`}
          >
            리포트 상세 보기
          </Link>
        </div>
      )}
      {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
    </section>
  );
}
