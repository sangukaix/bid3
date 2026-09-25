"use client";
import { useEffect, useRef, useState } from "react";
import { type Slide } from "./api";
import SlidePreview from "./SlidePreview";

function PageImage({ project, revision, slide, viewport }: {
  project: string; revision: number; slide: Slide; viewport: React.RefObject<HTMLDivElement | null>;
}) {
  const container = useRef<HTMLDivElement>(null);
  const [nearby, setNearby] = useState(false);
  useEffect(() => {
    const observer = new IntersectionObserver(([entry]) => setNearby(entry.isIntersecting), {
      root: viewport.current, rootMargin: "600px 0px",
    });
    if (container.current) observer.observe(container.current);
    return () => observer.disconnect();
  }, [viewport]);
  return <div ref={container} style={{ aspectRatio: `${slide.width || 16} / ${slide.height || 9}` }} className="overflow-hidden rounded-xl bg-white">
    {nearby ? <SlidePreview project={project} revision={revision} page={slide.number} /> : <div className="flex h-full items-center justify-center text-xs text-slate-400">{slide.number}쪽</div>}
  </div>;
}

export default function SlideDeck({ project, revision, slides, page, protectedSlides, onSelect }: {
  project: string; revision: number; slides: Slide[]; page: number; protectedSlides: number[]; onSelect: (page: number) => void;
}) {
  const viewport = useRef<HTMLDivElement>(null);
  const cards = useRef(new Map<number, HTMLElement>());
  function jump(number: number) {
    const card = cards.current.get(number);
    const area = viewport.current;
    if (card && area) area.scrollTo({ top: area.scrollTop + card.getBoundingClientRect().top - area.getBoundingClientRect().top - 16 });
  }
  useEffect(() => { jump(page); }, [page]);
  return <div className="overflow-hidden rounded-2xl border border-violet-100 bg-slate-100/80">
    <div className="flex items-center justify-between border-b border-slate-200 bg-white px-4 py-3 text-xs">
      <span className="font-semibold text-slate-700">전체 슬라이드 · {slides.length}쪽</span><span className="text-violet-700">편집 선택: {page}쪽</span>
    </div>
    <div className="flex h-[72vh] min-h-80 max-h-[1000px]">
      <nav aria-label="슬라이드 번호" className="w-14 shrink-0 space-y-2 overflow-y-auto border-r border-slate-200 bg-white p-2 sm:w-16">
        {slides.map(slide => <button key={slide.number} type="button" title={`${slide.number}쪽 · ${slide.title}`} aria-label={`${slide.number}쪽으로 이동${protectedSlides.includes(slide.number) ? " (원본 유지)" : ""}`} aria-current={page === slide.number ? "page" : undefined} onClick={() => { onSelect(slide.number); jump(slide.number); }} className={`relative h-10 w-full rounded-lg text-sm font-semibold transition ${page === slide.number ? "bg-violet-700 text-white shadow-sm" : "bg-slate-50 text-slate-600 hover:bg-violet-50"}`}>
          {slide.number}{protectedSlides.includes(slide.number) && <span className="absolute right-1 top-0.5 text-[8px]" aria-hidden="true">●</span>}
        </button>)}
      </nav>
      <div ref={viewport} role="region" aria-label="전체 슬라이드 미리보기" tabIndex={0} className="min-w-0 flex-1 space-y-6 overflow-y-auto overscroll-contain p-3 sm:p-5">
        {slides.map(slide => <article key={slide.number} ref={node => { if (node) cards.current.set(slide.number, node); else cards.current.delete(slide.number); }} aria-label={`${slide.number}쪽 슬라이드`} className={`rounded-2xl p-2 ${page === slide.number ? "bg-violet-100 ring-2 ring-violet-400" : "bg-white/60"}`}>
          <div className="flex items-center justify-between gap-2 px-1 pb-2 text-xs">
            <h2 className="min-w-0 truncate font-semibold text-slate-700">{slide.number} · {slide.title || "제목 없음"}</h2>
            <button type="button" onClick={() => onSelect(slide.number)} className="shrink-0 rounded-md px-2 py-1 text-violet-700 hover:bg-white">{page === slide.number ? "선택됨" : "편집 선택"}</button>
          </div>
          <PageImage project={project} revision={revision} slide={slide} viewport={viewport} />
        </article>)}
      </div>
    </div>
  </div>;
}
