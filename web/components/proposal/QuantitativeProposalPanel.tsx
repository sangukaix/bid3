"use client"; // 공고의 정량평가 요구사항을 확인하고 Word 작성안을 내려받는 화면

import { useEffect, useState } from "react";

import { API_BASE_URL } from "@/lib/api";
import type {
  BidQuantitativeProposalData,
  BidQuantitativeProposalResponse,
} from "@/types/bid";

export default function QuantitativeProposalPanel({
  bidNtceNo,
}: {
  bidNtceNo: string;
}) {
  const [proposal, setProposal] =
    useState<BidQuantitativeProposalData | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const token = localStorage.getItem("auth_token");
    if (!token) return;

    void fetch(
      `${API_BASE_URL}/api/bids/${bidNtceNo}/quantitative-proposal/`,
      { headers: { Authorization: `Token ${token}` } },
    )
      .then((response) => response.json())
      .then((data: BidQuantitativeProposalResponse) =>
        setProposal(data.quantitative_proposal),
      )
      .catch(() => setError("정량평가 작성안을 불러오지 못했습니다."));
  }, [bidNtceNo]);

  async function generateProposal(regenerate = false) {
    const token = localStorage.getItem("auth_token");
    if (!token || isGenerating) return;
    if (
      !window.confirm(
        regenerate
          ? "기존 작성안을 지우고 정량평가 양식을 다시 작성할까요?"
          : "공고 문서에서 정량평가 양식을 찾고 작성할까요?",
      )
    ) {
      return;
    }

    setIsGenerating(true);
    setError("");
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/bids/${bidNtceNo}/quantitative-proposal/`,
        {
          method: "POST",
          headers: {
            Authorization: `Token ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ regenerate }),
        },
      );
      const data = (await response.json().catch(() => ({}))) as
        BidQuantitativeProposalResponse & { error?: string };
      if (!response.ok || !data.quantitative_proposal) {
        throw new Error(data.error || "정량평가 작성안을 만들지 못했습니다.");
      }
      setProposal(data.quantitative_proposal);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "정량평가 작성안을 만들지 못했습니다.",
      );
    } finally {
      setIsGenerating(false);
    }
  }

  async function downloadProposal() {
    const token = localStorage.getItem("auth_token");
    if (!token || !proposal?.download_url) return;

    const response = await fetch(`${API_BASE_URL}${proposal.download_url}`, {
      headers: { Authorization: `Token ${token}` },
    });
    if (!response.ok) {
      setError("정량평가 Word 작성안을 내려받지 못했습니다.");
      return;
    }

    const objectUrl = URL.createObjectURL(await response.blob());
    const link = document.createElement("a");
    link.href = objectUrl;
    link.download = `bid2-quantitative-${bidNtceNo}.docx`;
    link.click();
    URL.revokeObjectURL(objectUrl);
  }

  const report = proposal?.report;
  const forms = report?.forms ?? [];
  const completion = report?.completion;
  const remainingFields = [
    ...(report?.incomplete_field_names ?? []),
    ...(report?.direct_review_field_names ?? []),
  ];

  return (
    <section className="app-panel mt-5 overflow-hidden rounded-lg border">
      <header className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 px-5 py-4 sm:px-6">
        <div>
          <h2 className="text-base font-bold text-slate-950">정량평가 자료</h2>
          <p className="mt-1 text-xs text-slate-500">
            첨부된 정량평가 양식을 찾아 회사 자료로 작성할 수 있는 칸을 채웁니다.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {proposal?.download_url && (
            <button
              className="cursor-pointer rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700"
              onClick={() => void downloadProposal()}
              type="button"
            >
              Word 작성안 내려받기
            </button>
          )}
          <button
            className="inline-flex cursor-pointer items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-slate-300"
            disabled={isGenerating}
            onClick={() => void generateProposal(Boolean(proposal))}
            type="button"
          >
            {isGenerating && (
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-blue-200 border-t-white" />
            )}
            {isGenerating ? "양식 작성 중..." : proposal ? "양식 다시 작성" : "양식 자동 작성"}
          </button>
        </div>
      </header>

      {report ? (
        <div className="px-5 py-5 sm:px-6">
          <div className="grid gap-3 sm:grid-cols-4">
            {[
              ["확인된 양식", completion?.form_count ?? forms.length],
              ["전체 항목", completion?.total_fields ?? 0],
              ["작성 완료", completion?.completed_fields ?? 0],
              ["남은 항목", remainingFields.length],
            ].map(([label, value]) => (
              <div className="rounded-md bg-slate-50 px-4 py-3" key={label}>
                <p className="text-xs text-slate-500">{label}</p>
                <p className="mt-1 text-xl font-bold text-slate-900">{value}</p>
              </div>
            ))}
          </div>

          {forms.length > 0 ? (
            <div className="mt-5 grid gap-2 sm:grid-cols-2">
              {forms.map((form) => {
                const completed = form.fields.filter((field) => field.status === "작성 완료").length;
                return (
                  <div className="rounded-md border border-slate-200 px-4 py-3" key={`${form.form_name}-${form.source_location}`}>
                    <p className="truncate text-sm font-semibold text-slate-900">{form.form_name}</p>
                    <p className="mt-1 text-xs text-slate-500">{completed}/{form.fields.length}개 작성</p>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="mt-4 text-sm text-slate-500">기존 작성안입니다. ‘양식 다시 작성’을 누르면 새 방식으로 정리됩니다.</p>
          )}

          {remainingFields.length > 0 && (
            <div className="mt-5 border-t border-slate-200 pt-4">
              <h3 className="text-sm font-bold text-slate-900">남은 작성 항목</h3>
              <ul className="mt-2 grid gap-2 text-sm text-slate-600 sm:grid-cols-2">
                {remainingFields.map((item) => (
                  <li className="truncate before:mr-2 before:text-rose-400 before:content-['•']" key={item}>{item}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      ) : (
        <p className="px-5 py-5 text-sm text-slate-500 sm:px-6">
          아직 작성된 정량평가 양식이 없습니다.
        </p>
      )}

      {error && <p className="border-t border-slate-200 px-5 py-3 text-sm text-red-600">{error}</p>}
    </section>
  );
}
