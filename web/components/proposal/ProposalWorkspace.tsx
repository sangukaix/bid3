"use client"; // 공고별 제안서 생성, 미리보기, AI비서를 한 화면에서 관리

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import LoginRequiredNotice from "@/components/auth/LoginRequiredNotice";
import CompanyClaimReviewPanel from "@/components/proposal/CompanyClaimReviewPanel";
import ProposalOutputReviewPanel from "@/components/proposal/ProposalOutputReviewPanel";
import ProposalPlanningPanel from "@/components/proposal/ProposalPlanningPanel";
import ProposalFinalReviewPanel from "@/components/proposal/ProposalFinalReviewPanel";
import ProposalSubmissionPanel from "@/components/proposal/ProposalSubmissionPanel";
import ProposalAssistant from "@/components/proposal/ProposalAssistant";
import ProposalPreviewModal from "@/components/proposal/ProposalPreviewModal";
import ProjectAnalysisCard from "@/components/proposal/ProjectAnalysisCard";
import ProjectReferenceDocuments from "@/components/proposal/ProjectReferenceDocuments";
import QuantitativeProposalPanel from "@/components/proposal/QuantitativeProposalPanel";
import TemplateGallery from "@/components/proposal/TemplateGallery";
import { API_BASE_URL } from "@/lib/api";
import { formatBidAmount } from "@/lib/bidFormat";
import type {
  BidNotice,
  BidProposalData,
  BidProposalResponse,
  ProposalTemplateOption,
  ProposalTaskData,
} from "@/types/bid";

export default function ProposalWorkspace({ bidNtceNo }: { bidNtceNo: string }) {
  const router = useRouter();
  const [bid, setBid] = useState<BidNotice | null>(null);
  const [proposal, setProposal] = useState<BidProposalData | null>(null);
  const [templates, setTemplates] = useState<ProposalTemplateOption[]>([]);
  const [selectedTemplateId, setSelectedTemplateId] = useState("");
  const [recommendedTemplateId, setRecommendedTemplateId] = useState("");
  const [templateRecommendationReason, setTemplateRecommendationReason] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [generationRequested, setIsGenerating] = useState(false);
  const [isFinalizing, setIsFinalizing] = useState(false);
  const [reviewRequested, setIsReviewingOutput] = useState(false);
  const [proposalTask,setProposalTask] = useState<ProposalTaskData | null>(null);
  const taskActive = proposalTask?.status==="queued" || proposalTask?.status==="running";
  const isGenerating = generationRequested || (taskActive && proposalTask?.kind==="generate");
  const isReviewingOutput = reviewRequested || (taskActive && proposalTask?.kind==="review");
  const [layoutAcknowledgedFor, setLayoutAcknowledgedFor] = useState("");
  const [previewUrl, setPreviewUrl] = useState("");
  const [isPreviewLoading, setIsPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState("");
  const [isPreviewModalOpen, setIsPreviewModalOpen] = useState(false);
  const [selectedPreviewPage, setSelectedPreviewPage] = useState(1);
  const [reviewPage, setReviewPage] = useState<number>();
  const [needsLogin, setNeedsLogin] = useState(false);
  const [error, setError] = useState("");
  const [isDeletingProject, setIsDeletingProject] = useState(false);

  async function refreshOutputReview(full = false) {
    const token = localStorage.getItem("auth_token");
    if (!token || !proposal) return;
    setIsReviewingOutput(true);
    setError("");
    try {
      const response = await fetch(`${API_BASE_URL}/api/bids/${bidNtceNo}/proposal/${full ? "full-review" : "output-review"}/`, {
        method: "POST", headers: { Authorization: `Token ${token}`, "Content-Type":"application/json" },
        body:JSON.stringify({async:full}),
      });
      const data = (await response.json()) as BidProposalResponse & { error?: string; task?:ProposalTaskData };
      if (response.status===202 && data.task) {setProposalTask(data.task);return;}
      if (!response.ok || !data.proposal) throw new Error(data.error ?? "최신 파일을 대조하지 못했습니다.");
      setProposal(data.proposal);
    } catch (error) { setError(error instanceof Error ? error.message : "파일 대조 중 오류가 발생했습니다."); }
    finally { setIsReviewingOutput(false); }
  }

  useEffect(() => {
    async function loadWorkspace() {
      const token = localStorage.getItem("auth_token");
      if (!token) {
        setNeedsLogin(true);
        setIsLoading(false);
        return;
      }

      try {
        const proposalResponse = await fetch(
          `${API_BASE_URL}/api/bids/${bidNtceNo}/proposal/`,
          { headers: { Authorization: `Token ${token}` } },
        );

        if (!proposalResponse.ok) {
          throw new Error("공고 작업 정보를 불러오지 못했습니다.");
        }

        const proposalData = (await proposalResponse.json()) as BidProposalResponse;
        const availableTemplates = proposalData.templates ?? [];
        const currentProposal =
          proposalData.proposal?.revision_plan.version === "template_generation_v1"
            ? proposalData.proposal
            : null; // 예전 원본-PPT 수정 결과는 새 제안서 미리보기로 사용하지 않음
        const currentTemplateId =
          currentProposal?.revision_plan.template_id ??
          availableTemplates.find((item) => item.available && item.id === localStorage.getItem("bid3_preferred_template"))?.id ??
          proposalData.selected_template_id ??
          availableTemplates.find((item) => item.available)?.id ??
          "";

        setBid(proposalData.item);
        setProposal(currentProposal);
        const taskResponse=await fetch(`${API_BASE_URL}/api/bids/${bidNtceNo}/proposal/task/`,{headers:{Authorization:`Token ${token}`}});
        if (taskResponse.ok) {
          const taskData=await taskResponse.json();setProposalTask(taskData.task);
          if (taskData.task?.status==="failed") setError(taskData.task.error);
        }
        setTemplates(availableTemplates);
        setSelectedTemplateId(currentTemplateId);
        setRecommendedTemplateId(proposalData.recommended_template_id ?? "");
        setTemplateRecommendationReason(
          proposalData.template_recommendation_reason ?? "",
        );
      } catch (requestError) {
        setError(
          requestError instanceof Error
            ? requestError.message
            : "작업 공간을 불러오지 못했습니다.",
        );
      } finally {
        setIsLoading(false);
      }
    }

    void loadWorkspace();
  }, [bidNtceNo]);

  useEffect(()=> {
    if (!taskActive) return;
    const token=localStorage.getItem("auth_token");
    if (!token) return;
    let cancelled=false;let inFlight=false;
    async function poll() {
      if (inFlight) return;
      inFlight=true;
      try {
        const response=await fetch(`${API_BASE_URL}/api/bids/${bidNtceNo}/proposal/task/`,{headers:{Authorization:`Token ${token}`}});
        if (!response.ok) throw new Error("작업 상태를 읽지 못했습니다. 연결을 확인해 주세요.");
        const data=await response.json();
        if (!cancelled) {
          setProposalTask(data.task);
          if (data.proposal) setProposal(data.proposal);
          if (data.task?.status==="failed") setError(data.task.error);
        }
      } catch (error) {if (!cancelled) setError(error instanceof Error ? error.message : "작업 상태 확인 실패");}
      finally {inFlight=false;}
    }
    void poll();const timer=window.setInterval(()=>void poll(),3000);
    return ()=>{cancelled=true;window.clearInterval(timer);};
  },[bidNtceNo,taskActive,proposalTask?.id]);

  useEffect(() => {
    if (!proposal || isGenerating || proposal.status === "generating") {
      return;
    }

    const token = localStorage.getItem("auth_token");
    if (!token) return;

    const previewPath = proposal.preview_url;
    let objectUrl = "";
    let cancelled = false;

    async function loadPreview() {
      setIsPreviewLoading(true);
      setPreviewError("");
      try {
        const response = await fetch(`${API_BASE_URL}${previewPath}`, {
          headers: { Authorization: `Token ${token}` },
        });
        if (!response.ok) {
          const data = (await response.json().catch(() => ({}))) as {
            error?: string;
          };
          throw new Error(data.error ?? "제안서 미리보기를 만들지 못했습니다.");
        }

        objectUrl = URL.createObjectURL(await response.blob());
        if (!cancelled) setPreviewUrl(objectUrl);
      } catch (requestError) {
        if (!cancelled) {
          setPreviewError(
            requestError instanceof Error
              ? requestError.message
              : "제안서 미리보기를 만들지 못했습니다.",
          );
        }
      } finally {
        if (!cancelled) setIsPreviewLoading(false);
      }
    }

    void loadPreview();
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [bidNtceNo, isGenerating, proposal]);

  async function generateProposal() {
    const token = localStorage.getItem("auth_token");
    if (!token || !selectedTemplateId) return;
    if (
      !window.confirm(
        proposal
          ? "작업한 내용이 사라집니다. 처음으로 되돌리시겠습니까?"
          : "선택한 템플릿으로 제안서를 생성하시겠습니까?",
      )
    ) {
      return;
    }

    setIsGenerating(true);
    setPreviewUrl("");
    setError("");
    try {
      const response = await fetch(`${API_BASE_URL}/api/bids/${bidNtceNo}/proposal/`, {
        method: "POST",
        headers: {
          Authorization: `Token ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          generation_mode: "default_template",
          template_id: selectedTemplateId,
          regenerate: Boolean(proposal),
          async: true,
        }),
      });
      const data = (await response.json().catch(() => ({}))) as BidProposalResponse & {
        error?: string;
        task?: ProposalTaskData;
      };
      if (response.status===202 && data.task) {setProposalTask(data.task);return;}
      if (!response.ok || !data.proposal) {
        throw new Error(data.error ?? "제안서를 생성하지 못했습니다.");
      }

      setProposal(data.proposal);
      window.dispatchEvent(new Event("proposal-projects-updated"));
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "제안서 생성에 실패했습니다.",
      );
    } finally {
      setIsGenerating(false);
    }
  }

  async function finalizeProposal() {
    const token = localStorage.getItem("auth_token");
    if (!token || !proposal) return;

    setIsFinalizing(true);
    setError("");
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/bids/${bidNtceNo}/proposal/finalize/`,
        {
          method: "POST",
          headers: { Authorization: `Token ${token}`, "Content-Type": "application/json" },
          body: JSON.stringify({ acknowledge_layout_warnings: layoutAcknowledgedFor === `${proposal.id}:${proposal.updated_at}` }),
        },
      );
      const data = (await response.json().catch(() => ({}))) as
        BidProposalResponse & { error?: string };
      if (data.proposal) setProposal(data.proposal);
      if (!response.ok || !data.proposal) {
        throw new Error(data.error ?? "제안서를 최종본으로 만들지 못했습니다.");
      }
      setProposal(data.proposal);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "제안서를 최종본으로 만들지 못했습니다.",
      );
    } finally {
      setIsFinalizing(false);
    }
  }

  async function downloadProposal() {
    const token = localStorage.getItem("auth_token");
    if (!token || !proposal) return;

    setError("");
    const response = await fetch(`${API_BASE_URL}${proposal.download_url}`, {
      headers: { Authorization: `Token ${token}` },
    });
    if (!response.ok) {
      setError("완성된 제안서를 내려받지 못했습니다.");
      return;
    }

    const url = URL.createObjectURL(await response.blob());
    const link = document.createElement("a");
    link.href = url;
    link.download = `bid2-proposal-${bidNtceNo}.pptx`;
    link.click();
    URL.revokeObjectURL(url);
  }

  async function deleteProject() {
    if (
      !window.confirm(
        "해당 프로젝트를 휴지통으로 이동하시겠습니까? 작업 내용은 휴지통에서 복원할 수 있습니다.",
      )
    ) return;

    const token = localStorage.getItem("auth_token");
    if (!token) return;
    setIsDeletingProject(true);
    setError("");
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/saved-bids/${bidNtceNo}/proposal-project/`,
        { method: "DELETE", headers: { Authorization: `Token ${token}` } },
      );
      if (!response.ok) {
        const data = (await response.json().catch(() => ({}))) as { error?: string };
        throw new Error(data.error || "프로젝트를 휴지통으로 이동하지 못했습니다.");
      }
      window.dispatchEvent(new Event("proposal-projects-updated"));
      router.push("/dashBoard/matchBid");
      router.refresh();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "프로젝트를 휴지통으로 이동하지 못했습니다.");
      setIsDeletingProject(false);
    }
  }

  if (needsLogin) return <LoginRequiredNotice />;
  if (isLoading) {
    return (
      <p className="py-20 text-center text-sm text-slate-500">
        작업 공간을 불러오는 중입니다.
      </p>
    );
  }
  if (!bid) {
    return <p className="rounded-md bg-red-50 p-5 text-sm text-red-600">{error}</p>;
  }

  const revisionPlan = proposal?.revision_plan;
  const canGenerate = templates.some(
    (item) => item.id === selectedTemplateId && item.available,
  ) && !isGenerating && !isReviewingOutput && !isFinalizing;
  const assistantDisabled = isGenerating || isFinalizing || isReviewingOutput || proposal?.status === "generating";

  return (
    <section className="min-w-0">
      <header className="flex items-start justify-between gap-5 border-b border-slate-200 pb-5">
        <div className="min-w-0">
        <Link
          className="text-sm font-semibold text-blue-600 hover:text-blue-700"
          href="/dashBoard/matchBid"
        >
          내가 저장한 공고
        </Link>
        <div className="mt-3 min-w-0 max-w-4xl">
          <h1 className="break-keep text-xl font-bold leading-8 text-slate-950">
            {bid.bidNtceNm}
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            {bid.bsnsDivNm || "구분 확인 필요"} · {formatBidAmount(bid)} · 마감{" "}
            {bid.bidClseDate || "확인 필요"}
          </p>
        </div>
        </div>
        <button
          className="shrink-0 cursor-pointer px-2 py-1 text-xs font-semibold text-red-600 hover:text-red-800 disabled:cursor-not-allowed disabled:text-slate-300"
          disabled={isDeletingProject || taskActive}
          onClick={() => void deleteProject()}
          type="button"
        >
          {isDeletingProject ? "이동 중..." : "프로젝트 휴지통으로 이동"}
        </button>
      </header>

      {taskActive && <p role="status" className="mt-4 rounded-md border border-blue-200 bg-blue-50 p-4 text-sm text-blue-900">
        서버에서 {proposalTask?.kind==="generate" ? "제안서 생성·검수·보완" : "최종 문서 전체 검수"} 작업을 진행 중입니다. 다시 접속해도 작업 상태를 확인할 수 있습니다.
        {proposalTask?.progress && <span className="mt-1 block text-xs">{proposalTask.progress}</span>}
      </p>}
      {error && (
        <p className="mt-4 rounded-md bg-red-50 px-4 py-3 text-sm text-red-600">{error}</p>
      )}

      <div className="mt-5 grid min-w-0 gap-5 lg:grid-cols-[minmax(0,1fr)_350px]">
        <main className="app-panel min-w-0 overflow-hidden rounded-lg border">
          <div className="px-5 py-5 sm:px-6">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 pb-4">
              <h2 className="text-lg font-bold text-slate-950">제안서 생성</h2>
              {proposal && (
                <span
                  className={`rounded px-2 py-1 text-xs font-semibold ${
                    proposal.status === "final"
                      ? "bg-emerald-50 text-emerald-700"
                      : "bg-blue-50 text-blue-700"
                  }`}
                >
                  {proposal.status === "final" ? "최종본" : "초안"}
                </span>
              )}
            </div>

            <ProjectAnalysisCard bidNtceNo={bidNtceNo} />

            <ProjectReferenceDocuments
              bidNtceNo={bidNtceNo}
              disabled={isGenerating}
            />

            <div className="grid items-end gap-5 py-5 xl:grid-cols-[minmax(0,1fr)_210px]">
              <TemplateGallery
                onSelect={setSelectedTemplateId}
                recommendedTemplateId={recommendedTemplateId}
                recommendationReason={templateRecommendationReason}
                selectedTemplateId={selectedTemplateId}
                templates={templates}
              />
              {!isGenerating && (
                <div>
                  <button
                    className="w-full cursor-pointer rounded-md bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-slate-300"
                    disabled={!canGenerate}
                    onClick={generateProposal}
                    type="button"
                  >
                    {proposal ? "처음으로 되돌리기" : "제안서 생성"}
                  </button>
                  <p className="mt-2 text-center text-xs leading-5 text-slate-400">
                    문서 분량과 모델에 따라 시간이 걸립니다. 생성과 검수는 서버에서 이어집니다.
                  </p>
                </div>
              )}
            </div>

            {isGenerating && (
              <div className="mt-5 flex min-h-72 flex-col items-center justify-center border-t border-slate-200 text-center">
                <span
                  aria-hidden="true"
                  className="h-7 w-7 animate-spin rounded-full border-2 border-blue-100 border-t-blue-600"
                />
                <p className="mt-4 text-sm font-semibold text-slate-800">
                  모든 문서와 슬라이드를 분석하고 있습니다.
                </p>
              </div>
            )}

            {proposal && !isGenerating && (
              <div className="mt-5 border-t border-slate-200 pt-5">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <h3 className="text-sm font-bold text-slate-950">제안서 미리보기</h3>
                    <p className="mt-1 text-xs text-slate-500">
                      생성본 {revisionPlan?.output_slide_count ?? 0}쪽
                    </p>
                  </div>
                  {previewUrl && (
                    <button
                      className="cursor-pointer rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700"
                      onClick={() => setIsPreviewModalOpen(true)}
                      type="button"
                    >
                      전체 화면
                    </button>
                  )}
                </div>

                <div className="mt-4 min-h-[560px] overflow-hidden rounded-md border border-slate-200 bg-slate-100">
                  {isPreviewLoading ? (
                    <div className="flex h-[560px] items-center justify-center text-sm text-slate-500">
                      미리보기를 준비하는 중입니다.
                    </div>
                  ) : previewError ? (
                    <div className="flex h-[560px] items-center justify-center px-6 text-center text-sm text-red-600">
                      {previewError}
                    </div>
                  ) : previewUrl ? (
                    <div className="grid h-[560px] grid-cols-[48px_minmax(0,1fr)] bg-white">
                      <aside className="overflow-y-auto border-r border-slate-200 bg-slate-50 py-2">
                        {Array.from(
                          { length: revisionPlan?.output_slide_count ?? 0 },
                          (_, index) => index + 1,
                        ).map((page) => (
                          <button
                            aria-label={`${page}페이지 보기`}
                            className={`mx-auto mb-1 flex h-8 w-8 cursor-pointer items-center justify-center rounded text-xs ${
                              selectedPreviewPage === page
                                ? "bg-blue-600 font-semibold text-white"
                                : "text-slate-500 hover:bg-slate-200"
                            }`}
                            key={page}
                            onClick={() => setSelectedPreviewPage(page)}
                            type="button"
                          >
                            {page}
                          </button>
                        ))}
                      </aside>
                      <iframe
                        className="h-[560px] w-full bg-white"
                        key={selectedPreviewPage}
                        src={`${previewUrl}#page=${selectedPreviewPage}&view=FitH&toolbar=0&navpanes=0&scrollbar=1`}
                        title="제안서 미리보기"
                      />
                    </div>
                  ) : null}
                </div>

                <ProposalSubmissionPanel bidNtceNo={bidNtceNo} proposalUpdatedAt={proposal.updated_at}
                  busy={isGenerating || isReviewingOutput || isFinalizing} />
                <ProposalPlanningPanel plan={proposal.revision_plan.writing_plan}
                  onPage={page => { setSelectedPreviewPage(page); setReviewPage(page); }} />
                <ProposalFinalReviewPanel plan={proposal.revision_plan} busy={isReviewingOutput}
                  disabled={isGenerating || isFinalizing} onReview={()=>void refreshOutputReview(true)}
                  onPage={page => { setSelectedPreviewPage(page); setReviewPage(page); }} />
                <CompanyClaimReviewPanel plan={proposal.revision_plan} disabled={assistantDisabled}
                  onReviewPage={(page) => {
                    setSelectedPreviewPage(page); setReviewPage(page);
                    document.getElementById("proposal-assistant")?.scrollIntoView({ behavior: "smooth", block: "center" });
                    document.querySelector<HTMLTextAreaElement>("#proposal-assistant textarea")?.focus({ preventScroll: true });
                  }} />
                <ProposalOutputReviewPanel review={proposal.revision_plan.output_review}
                  disabled={isGenerating || isFinalizing} refreshing={isReviewingOutput} onRefresh={()=>void refreshOutputReview()}
                  onPage={page => { setSelectedPreviewPage(page); setReviewPage(page); }} />
                {!!proposal.revision_plan.quality_review?.review_items?.length && (
                  <div className="mt-4 rounded-md border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950">
                    <h4 className="font-semibold">출력 전 확인할 내용</h4>
                    <ul className="mt-2 list-disc space-y-1 pl-5 text-xs leading-5">
                      {proposal.revision_plan.quality_review.review_items.map((item, i) => <li key={i}>{item}</li>)}
                    </ul>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {[...new Set([
                        ...(proposal.revision_plan.quality_review.unresolved_placeholders ?? []),
                        ...(proposal.revision_plan.quality_review.template_leftovers ?? []),
                        ...(proposal.revision_plan.quality_review.severe_overflow_items ?? []),
                      ].map(item => item.slide_number))].sort((a, b) => a - b).map(page => (
                        <button key={page} type="button" className="cursor-pointer rounded border border-amber-300 bg-white px-2 py-1 text-xs"
                          onClick={() => { setSelectedPreviewPage(page); setReviewPage(page); }}>{page}쪽 확인</button>
                      ))}
                    </div>
                    {!!proposal.revision_plan.quality_review.severe_overflow_items?.length && proposal.status === "draft" && (
                      <label className="mt-3 flex items-start gap-2 text-xs leading-5">
                        <input type="checkbox" className="mt-1" checked={layoutAcknowledgedFor === `${proposal.id}:${proposal.updated_at}`}
                          onChange={e => setLayoutAcknowledgedFor(e.target.checked ? `${proposal.id}:${proposal.updated_at}` : "")} />
                        미리보기에서 표시된 페이지의 글자 겹침과 잘림이 없음을 확인했습니다.
                      </label>
                    )}
                  </div>
                )}
                <div className="mt-4 flex justify-end gap-2">
                  {proposal.status === "draft" ? (
                    <button
                      className="cursor-pointer rounded-md bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-slate-300"
                      disabled={isFinalizing || isPreviewLoading || isReviewingOutput}
                      onClick={() => void finalizeProposal()}
                      type="button"
                    >
                      {isFinalizing ? "최종본 생성 중..." : "제안서 만들기"}
                    </button>
                  ) : (
                    <button
                      className="cursor-pointer rounded-md bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-700"
                      onClick={() => void downloadProposal()}
                      type="button"
                    >
                      최종 제안서 내려받기
                    </button>
                  )}
                </div>
              </div>
            )}
          </div>
        </main>

        <aside id="proposal-assistant" className="app-panel min-w-0 overflow-hidden rounded-lg border lg:h-[820px]">
          <ProposalAssistant
            bidNtceNo={bidNtceNo}
            bidTitle={bid.bidNtceNm}
            disabled={assistantDisabled}
            onUpdated={setProposal}
            proposal={proposal}
            selectedSlide={reviewPage}
            onClearSelection={() => setReviewPage(undefined)}
          />
        </aside>
      </div>

      <QuantitativeProposalPanel bidNtceNo={bidNtceNo} />

      {isPreviewModalOpen && previewUrl && (
        <ProposalPreviewModal
          onClose={() => setIsPreviewModalOpen(false)}
          previewUrl={previewUrl}
          renderAssistant={(selectedPage) => (
            <ProposalAssistant
              bidNtceNo={bidNtceNo}
              bidTitle={bid.bidNtceNm}
              disabled={assistantDisabled}
              onUpdated={setProposal}
              proposal={proposal}
              selectedSlide={selectedPage}
            />
          )}
          slideCount={revisionPlan?.output_slide_count ?? 0}
        />
      )}
    </section>
  );
}
