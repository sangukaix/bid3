"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { API_BASE_URL } from "@/lib/api";
import type { ProposalTemplateOption } from "@/types/bid";

type Props = {
  templates: ProposalTemplateOption[];
  selectedTemplateId: string;
  recommendedTemplateId: string;
  recommendationReason: string;
  onSelect: (templateId: string) => void;
};

function authorization() {
  const token = localStorage.getItem("auth_token");
  if (!token) throw new Error("로그인 후 템플릿을 확인할 수 있습니다.");
  return { Authorization: `Token ${token}` };
}

function SlideImage({ template, page, eager = false }: {
  template: ProposalTemplateOption; page: number; eager?: boolean;
}) {
  const frame = useRef<HTMLDivElement>(null);
  const [url, setUrl] = useState("");
  const [error, setError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    let objectUrl = "";
    let started = false;
    async function load() {
      if (started) return;
      started = true;
      try {
        const response = await fetch(`${API_BASE_URL}${template.preview_url}${page}/`, {
          headers: authorization(), signal: controller.signal,
        });
        if (!response.ok) throw new Error("미리보기를 불러오지 못했습니다.");
        const blob = await response.blob();
        if (controller.signal.aborted) return;
        objectUrl = URL.createObjectURL(blob);
        setUrl(objectUrl);
      } catch (cause) {
        if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : "미리보기 오류");
      }
    }
    const observer = new IntersectionObserver((entries) => {
      if (entries.some((entry) => entry.isIntersecting)) { void load(); observer.disconnect(); }
    }, { rootMargin: "120px" });
    if (eager) void load();
    else if (frame.current) observer.observe(frame.current);
    return () => { controller.abort(); observer.disconnect(); if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [template.preview_url, page, eager]);
  return <div ref={frame} className="relative aspect-video w-full overflow-hidden bg-slate-100">
    {url ? (
      // Authenticated object URLs cannot use the Next.js image optimizer.
      // eslint-disable-next-line @next/next/no-img-element
      <img src={url} alt={`${template.name} ${page}페이지`} className="h-full w-full object-contain" />
    ) : <div className="flex h-full items-center justify-center px-4 text-center text-xs text-slate-500" role="status">{error || "미리보기 준비 중"}</div>}
  </div>;
}

export default function TemplateGallery({ templates, selectedTemplateId, recommendedTemplateId, recommendationReason, onSelect }: Props) {
  const [open, setOpen] = useState(false);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("전체");
  const [downloadError, setDownloadError] = useState("");
  const [downloading, setDownloading] = useState(false);
  const dialog = useRef<HTMLDialogElement>(null);
  const selected = templates.find((t) => t.id === selectedTemplateId);
  const active = templates.find((t) => t.id === activeId);
  const categories = useMemo(() => ["전체", ...new Set(templates.map((t) => t.category || "기본 양식"))], [templates]);
  const filtered = useMemo(() => {
    const words = query.trim().toLowerCase().split(/\s+/).filter(Boolean);
    return templates.filter((t) => (category === "전체" || (t.category || "기본 양식") === category)
      && words.every((word) => `${t.name} ${t.description} ${t.category} ${(t.tags || []).join(" ")}`.toLowerCase().includes(word)));
  }, [templates, query, category]);
  useEffect(() => {
    const element = dialog.current;
    if (!open || !element) return;
    element.showModal();
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => { element.close(); document.body.style.overflow = overflow; };
  }, [open]);

  function preview(template: ProposalTemplateOption) { setActiveId(template.id); setPage(1); setDownloadError(""); }
  async function download(template: ProposalTemplateOption) {
    if (!template.download_url || downloading) return;
    setDownloading(true); setDownloadError("");
    try {
      const response = await fetch(`${API_BASE_URL}${template.download_url}`, { headers: authorization() });
      if (!response.ok) throw new Error("PPTX 다운로드에 실패했습니다.");
      const url = URL.createObjectURL(await response.blob());
      const anchor = document.createElement("a");
      anchor.href = url; anchor.download = `${template.name}.pptx`; anchor.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (cause) { setDownloadError(cause instanceof Error ? cause.message : "다운로드 오류"); }
    finally { setDownloading(false); }
  }

  return <section className="min-w-0">
    <p className="mb-2 text-xs font-semibold text-slate-500">디자인 템플릿</p>
    <button type="button" onClick={() => { setActiveId(null); setOpen(true); }} className="flex w-full max-w-xl cursor-pointer items-center justify-between gap-4 rounded-lg border border-slate-300 bg-white px-4 py-3 text-left hover:border-blue-400 hover:bg-blue-50">
      <span><span className="block text-sm font-semibold text-slate-900">디자인 템플릿 선택하기</span><span className="mt-1 block text-xs text-slate-500">{templates.length}종 · 현재 선택: {selected?.name || "선택 전"}</span></span><span aria-hidden="true" className="text-xl text-slate-400">›</span>
    </button>
    {open && <dialog ref={dialog} aria-labelledby="template-dialog-title" onCancel={() => setOpen(false)} onClick={(e) => { if (e.target === e.currentTarget) setOpen(false); }} className="fixed inset-0 m-auto h-[92dvh] max-h-[1000px] w-[96vw] max-w-7xl rounded-xl bg-slate-50 p-0 text-slate-900 shadow-2xl backdrop:bg-slate-950/60">
      <div className="flex h-full flex-col">
        <header className="flex shrink-0 items-center justify-between gap-4 border-b border-slate-200 bg-white px-5 py-4">
          <div className="flex items-center gap-3">
            {active && <button type="button" onClick={() => setActiveId(null)} className="cursor-pointer rounded-md border border-slate-200 px-3 py-2 text-sm hover:bg-slate-50">← 목록</button>}
            <div><h2 id="template-dialog-title" className="text-lg font-bold">{active?.name || "제안서 디자인 라이브러리"}</h2><p className="mt-1 text-xs text-slate-500">{active ? `${active.slide_count}쪽 · ${active.category || "기본 양식"}` : "실제 슬라이드를 살펴보고 사업에 맞는 양식을 고르세요."}</p></div>
          </div>
          <button type="button" aria-label="템플릿 선택 닫기" onClick={() => setOpen(false)} className="h-9 w-9 shrink-0 cursor-pointer rounded-md text-xl hover:bg-slate-100">×</button>
        </header>
        {!active ? <>
          <div className="shrink-0 border-b border-slate-200 bg-white p-4 sm:px-6">
            <label className="block"><span className="sr-only">템플릿 검색</span><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="이름, 용도, 분위기로 검색" className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm outline-none focus:border-blue-500 sm:max-w-md" /></label>
            <div className="mt-3 flex gap-2 overflow-x-auto pb-1" aria-label="템플릿 용도">{categories.map((item) => <button type="button" key={item} aria-pressed={category === item} onClick={() => setCategory(item)} className={`shrink-0 cursor-pointer rounded-full px-3 py-1.5 text-xs font-medium ${category === item ? "bg-slate-900 text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"}`}>{item}</button>)}</div>
          </div>
          <div className="min-h-0 flex-1 overflow-y-auto p-4 sm:p-6">
            <p className="mb-4 text-xs text-slate-500" role="status">{filtered.length}종의 템플릿</p>
            {filtered.length === 0 && <p className="py-16 text-center text-sm text-slate-500">검색 결과가 없습니다. 다른 검색어나 용도를 선택해 주세요.</p>}
            <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">{filtered.map((t) => <button type="button" key={t.id} disabled={!t.available} onClick={() => preview(t)} className={`group overflow-hidden rounded-lg border bg-white text-left shadow-sm transition hover:-translate-y-0.5 hover:shadow-md disabled:opacity-50 ${selectedTemplateId === t.id ? "border-blue-500 ring-1 ring-blue-500" : "border-slate-200"}`}>
              <SlideImage template={t} page={1} /><span className="block p-4"><span className="mb-1 flex items-center justify-between gap-2"><span className="text-sm font-bold">{t.name}</span>{selectedTemplateId === t.id ? <span className="text-xs font-semibold text-blue-700">선택됨</span> : recommendedTemplateId === t.id ? <span className="text-xs font-semibold text-emerald-700">추천</span> : null}</span><span className="block text-xs leading-5 text-slate-500">{t.description}</span><span className="mt-3 flex items-center justify-between text-[11px] text-slate-400"><span>{t.category || "기본 양식"}</span><span>{t.slide_count}쪽 · PPTX</span></span></span>
            </button>)}</div>
          </div>
        </> : <div className="grid min-h-0 flex-1 overflow-y-auto lg:grid-cols-[minmax(0,1fr)_290px]">
          <main className="min-w-0 p-4 sm:p-6">
            <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm"><SlideImage key={`${active.id}-${page}`} template={active} page={page} eager /></div>
            <div className="mt-4 flex items-center justify-between"><button type="button" disabled={page === 1} onClick={() => setPage((v) => v - 1)} className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm disabled:opacity-30">이전</button><p className="text-sm text-slate-600" aria-live="polite">{page} / {active.slide_count}페이지</p><button type="button" disabled={page === active.slide_count} onClick={() => setPage((v) => v + 1)} className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm disabled:opacity-30">다음</button></div>
            <div className="mt-4 flex flex-wrap gap-2" aria-label="슬라이드 페이지">{Array.from({ length: active.slide_count }, (_, i) => <button key={i} type="button" aria-label={`${i + 1}페이지 보기`} aria-pressed={page === i + 1} onClick={() => setPage(i + 1)} className={`h-9 min-w-9 rounded-md px-2 text-xs ${page === i + 1 ? "bg-slate-900 text-white" : "border border-slate-200 bg-white text-slate-600 hover:bg-slate-100"}`}>{i + 1}</button>)}</div>
          </main>
          <aside className="flex flex-col border-t border-slate-200 bg-white p-5 lg:border-l lg:border-t-0">
            <p className="text-xs font-semibold text-blue-700">{active.collection || "제안서 템플릿"}</p><h3 className="mt-2 text-xl font-bold">{active.name}</h3><p className="mt-3 text-sm leading-6 text-slate-600">{active.description}</p>
            <div className="mt-4 flex flex-wrap gap-2">{active.tags?.map((tag) => <span key={tag} className="rounded bg-slate-100 px-2 py-1 text-xs text-slate-600">{tag}</span>)}</div>
            {active.id === recommendedTemplateId && <p className="mt-5 rounded-lg bg-emerald-50 p-3 text-xs leading-5 text-emerald-800">추천: {recommendationReason}</p>}
            <p className="mt-5 text-xs leading-5 text-slate-500">본문과 표를 PowerPoint에서 수정할 수 있습니다. 선택한 양식으로 제안서를 생성하면 공고와 회사 자료를 반영합니다.</p>
            {active.license_note && <p className="mt-3 text-[11px] leading-5 text-slate-400">{active.license_note}</p>}
            <div className="mt-auto space-y-3 pt-8">{downloadError && <p role="alert" className="text-xs text-red-600">{downloadError}</p>}{active.download_url && <button type="button" disabled={downloading} onClick={() => void download(active)} className="w-full cursor-pointer rounded-lg border border-slate-300 px-4 py-2.5 text-sm font-semibold hover:bg-slate-50 disabled:opacity-50">{downloading ? "다운로드 중…" : "PPTX 양식 다운로드"}</button>}<button type="button" onClick={() => { onSelect(active.id); setOpen(false); }} className="w-full cursor-pointer rounded-lg bg-blue-600 px-4 py-3 text-sm font-semibold text-white hover:bg-blue-700">이 템플릿 선택</button></div>
          </aside>
        </div>}
      </div>
    </dialog>}
  </section>;
}
