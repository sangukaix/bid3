"use client"; // 템플릿 선택과 실제 슬라이드 미리보기 팝업 관리

import { useEffect, useState } from "react";

import { API_BASE_URL } from "@/lib/api";
import type { ProposalTemplateOption } from "@/types/bid";

type TemplateGalleryProps = {
  templates: ProposalTemplateOption[];
  selectedTemplateId: string;
  recommendedTemplateId: string;
  recommendationReason: string;
  onSelect: (templateId: string) => void;
};

async function fetchSlideImage(template: ProposalTemplateOption, page: number) {
  const token = localStorage.getItem("auth_token");
  if (!token) throw new Error("로그인 후 템플릿을 확인할 수 있습니다.");
  const response = await fetch(
    `${API_BASE_URL}${template.preview_url}${page}/`,
    { headers: { Authorization: `Token ${token}` } },
  );
  if (!response.ok) throw new Error("템플릿 미리보기를 만들지 못했습니다.");
  return URL.createObjectURL(await response.blob());
}

export default function TemplateGallery({
  templates,
  selectedTemplateId,
  recommendedTemplateId,
  recommendationReason,
  onSelect,
}: TemplateGalleryProps) {
  const [activeTemplate, setActiveTemplate] = useState<ProposalTemplateOption | null>(null);
  const [slideUrls, setSlideUrls] = useState<string[]>([]);
  const [viewMode, setViewMode] = useState<"scroll" | "grid">("scroll");
  const [isPreviewLoading, setIsPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState("");

  useEffect(() => {
    if (!activeTemplate) return;
    const template = activeTemplate;
    let cancelled = false;
    const createdUrls: string[] = [];

    async function loadSlides() {
      setIsPreviewLoading(true);
      setPreviewError("");
      try {
        const urls = await Promise.all(
          Array.from(
            { length: template.slide_count },
            (_, index) => fetchSlideImage(template, index + 1),
          ),
        );
        createdUrls.push(...urls);
        if (!cancelled) setSlideUrls(urls);
      } catch (error) {
        if (!cancelled) {
          setPreviewError(
            error instanceof Error ? error.message : "템플릿을 불러오지 못했습니다.",
          );
        }
      } finally {
        if (!cancelled) setIsPreviewLoading(false);
      }
    }

    void loadSlides();
    return () => {
      cancelled = true;
      createdUrls.forEach((url) => URL.revokeObjectURL(url));
    };
  }, [activeTemplate]);

  useEffect(() => {
    if (!activeTemplate) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [activeTemplate]);

  const selectedTemplate = templates.find(
    (template) => template.id === selectedTemplateId,
  );
  const recommendedTemplate = templates.find(
    (template) => template.id === recommendedTemplateId,
  );

  function openTemplatePicker() {
    const firstAvailable = templates.find((template) => template.available);
    setSlideUrls([]);
    setActiveTemplate(
      selectedTemplate?.available ? selectedTemplate : firstAvailable ?? null,
    );
  }

  return (
    <section className="min-w-0">
      <p className="mb-2 text-xs font-semibold text-slate-500">디자인 템플릿</p>
      <button
        className="flex w-full max-w-xl cursor-pointer items-center justify-between gap-4 rounded-md border border-slate-300 bg-white px-4 py-3 text-left transition-colors hover:border-blue-400 hover:bg-blue-50"
        onClick={openTemplatePicker}
        type="button"
      >
        <span className="min-w-0">
          <span className="block text-sm font-semibold text-slate-900">
            디자인 템플릿 선택하기
          </span>
          <span className="mt-0.5 block truncate text-xs text-slate-500">
            현재 선택: {selectedTemplate?.name ?? "템플릿을 선택해 주세요"}
          </span>
          {selectedTemplateId === recommendedTemplateId && recommendedTemplate && (
            <span className="mt-1 block text-xs font-semibold text-emerald-700">
              현재 프로젝트 추천 템플릿
            </span>
          )}
        </span>
        <span aria-hidden="true" className="shrink-0 text-lg text-slate-400">
          ›
        </span>
      </button>

      {activeTemplate && (
        <div className="fixed inset-0 z-[110] bg-slate-950/55 p-3 backdrop-blur-[1px] sm:p-6">
          <div className="mx-auto flex h-full max-w-7xl flex-col overflow-hidden rounded-lg bg-slate-50 shadow-2xl">
            <header className="flex shrink-0 items-center justify-between border-b border-slate-200 bg-white px-5 py-4">
              <div>
                <h3 className="text-base font-bold text-slate-950">디자인 템플릿 선택</h3>
                <p className="mt-0.5 text-xs text-slate-500">
                  제안 목적과 분위기에 맞는 디자인을 골라 주세요.
                </p>
              </div>
              <button
                aria-label="템플릿 선택 닫기"
                className="flex h-9 w-9 cursor-pointer items-center justify-center rounded-md text-xl text-slate-500 hover:bg-slate-100"
                onClick={() => setActiveTemplate(null)}
                type="button"
              >
                ×
              </button>
            </header>

            <div className="grid min-h-0 flex-1 lg:grid-cols-[280px_minmax(0,1fr)]">
              <aside className="border-b border-slate-200 bg-white p-3 lg:overflow-y-auto lg:border-b-0 lg:border-r">
                {recommendedTemplate && (
                  <div className="mb-3 rounded-md border border-emerald-200 bg-emerald-50 px-4 py-3">
                    <p className="text-xs font-semibold text-emerald-700">현재 프로젝트 추천</p>
                    <p className="mt-1 text-sm font-bold text-slate-900">
                      {recommendedTemplate.name}
                    </p>
                    <p className="mt-1 text-xs leading-5 text-slate-600">
                      {recommendationReason}
                    </p>
                    <button
                      className="mt-2 cursor-pointer text-xs font-semibold text-emerald-700 hover:text-emerald-800"
                      onClick={() => setActiveTemplate(recommendedTemplate)}
                      type="button"
                    >
                      추천 디자인 보기
                    </button>
                  </div>
                )}
                <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-1">
                  {templates.map((template) => (
                    <button
                      aria-pressed={activeTemplate.id === template.id}
                      className={`cursor-pointer rounded-md border px-4 py-3 text-left transition-colors disabled:cursor-not-allowed disabled:opacity-40 ${
                        activeTemplate.id === template.id
                          ? "border-blue-500 bg-blue-50"
                          : "border-slate-200 bg-white hover:border-blue-300 hover:bg-slate-50"
                      }`}
                      disabled={!template.available}
                      key={template.id}
                      onClick={() => setActiveTemplate(template)}
                      type="button"
                    >
                      <span className="flex items-center justify-between gap-2">
                        <span className="text-sm font-semibold text-slate-900">
                          {template.name}
                        </span>
                        {selectedTemplateId === template.id && (
                          <span className="shrink-0 rounded bg-blue-100 px-2 py-0.5 text-[11px] font-semibold text-blue-700">
                            선택됨
                          </span>
                        )}
                        {selectedTemplateId !== template.id && recommendedTemplateId === template.id && (
                          <span className="shrink-0 rounded bg-emerald-100 px-2 py-0.5 text-[11px] font-semibold text-emerald-700">
                            추천
                          </span>
                        )}
                      </span>
                      <span className="mt-1 block text-xs leading-5 text-slate-500">
                        {template.description}
                      </span>
                    </button>
                  ))}
                </div>
              </aside>

              <main className="flex min-h-0 flex-col">
                <div className="flex shrink-0 items-center justify-between border-b border-slate-200 bg-white px-4 py-3">
                  <div>
                    <p className="text-sm font-bold text-slate-900">{activeTemplate.name}</p>
                    <p className="text-xs text-slate-500">
                      {activeTemplate.slide_count}개 기본 레이아웃
                    </p>
                  </div>
                  <div className="flex rounded-md border border-slate-200 p-0.5">
                    <button
                      className={`cursor-pointer rounded px-3 py-1.5 text-xs ${viewMode === "scroll" ? "bg-blue-600 text-white" : "text-slate-600 hover:bg-slate-100"}`}
                      onClick={() => setViewMode("scroll")}
                      type="button"
                    >
                      크게 보기
                    </button>
                    <button
                      className={`cursor-pointer rounded px-3 py-1.5 text-xs ${viewMode === "grid" ? "bg-blue-600 text-white" : "text-slate-600 hover:bg-slate-100"}`}
                      onClick={() => setViewMode("grid")}
                      type="button"
                    >
                      전체 보기
                    </button>
                  </div>
                </div>

                <div className="min-h-0 flex-1 overflow-y-auto p-4 sm:p-5">
                  {isPreviewLoading && (
                    <div className="flex min-h-80 items-center justify-center gap-2 text-sm text-slate-500">
                      <span className="h-5 w-5 animate-spin rounded-full border-2 border-slate-300 border-t-blue-600" />
                      템플릿을 준비하는 중입니다.
                    </div>
                  )}
                  {previewError && (
                    <p className="py-20 text-center text-sm text-red-600">{previewError}</p>
                  )}
                  {!isPreviewLoading && !previewError && (
                    <div
                      className={
                        viewMode === "grid"
                          ? "grid gap-4 sm:grid-cols-2 xl:grid-cols-3"
                          : "mx-auto max-w-4xl space-y-5"
                      }
                    >
                      {slideUrls.map((url, index) => (
                        <figure
                          className="overflow-hidden rounded-md border border-slate-200 bg-white shadow-sm"
                          key={url}
                        >
                          {/* eslint-disable-next-line @next/next/no-img-element */}
                          <img
                            alt={`${index + 1}페이지`}
                            className="w-full"
                            loading="lazy"
                            src={url}
                          />
                          <figcaption className="border-t border-slate-100 px-3 py-1.5 text-xs text-slate-500">
                            {index + 1}페이지
                          </figcaption>
                        </figure>
                      ))}
                    </div>
                  )}
                </div>

                <footer className="flex shrink-0 items-center justify-end border-t border-slate-200 bg-white px-5 py-3">
                  <button
                    className="cursor-pointer rounded-md bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-700"
                    onClick={() => {
                      onSelect(activeTemplate.id);
                      setActiveTemplate(null);
                    }}
                    type="button"
                  >
                    이 템플릿 선택
                  </button>
                </footer>
              </main>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
