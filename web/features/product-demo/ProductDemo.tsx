"use client";

import Link from "next/link";
import { useRef, useState } from "react";
import storyboard from "./storyboard.json";

let start = 0;
const chapters = storyboard.scenes.map(scene => {
  const chapter = { ...scene, start };
  start += scene.duration;
  return chapter;
});
const duration = start;
function time(seconds: number) {
  return `${Math.floor(seconds / 60)}:${String(Math.floor(seconds % 60)).padStart(2, "0")}`;
}

export default function ProductDemo() {
  const video = useRef<HTMLVideoElement>(null);
  const pendingSeek = useRef<number | null>(null);
  const [current, setCurrent] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [error, setError] = useState(false);
  const currentChapter = chapters.findLastIndex(chapter => current >= chapter.start);
  const source = `${storyboard.video}?v=${storyboard.version}`;

  async function seek(seconds: number) {
    const player = video.current;
    if (!player) return;
    pendingSeek.current = seconds;
    if (player.readyState >= 1) {
      player.currentTime = seconds;
      pendingSeek.current = null;
    }
    try {
      await player.play();
      setError(false);
    } catch {
      // Native controls remain available if the browser declines scripted playback.
      setPlaying(false);
    }
  }

  return (
    <section id="product-demo" aria-labelledby="product-demo-title" className="scroll-mt-20 overflow-hidden bg-[#102630] text-white">
      <div className="mx-auto max-w-6xl px-5 py-14 sm:px-8 sm:py-20">
        <div className="mb-8 flex flex-wrap items-end justify-between gap-6">
          <div>
            <p className="text-xs font-semibold tracking-[0.18em] text-[#8ee0c7]">SEE IT IN ACTION</p>
            <h2 id="product-demo-title" className="mt-4 text-3xl font-bold leading-tight tracking-tight sm:text-4xl">자료가 문서가 되는 과정.<br /><span className="text-[#8ee0c7]">{duration}초로 만나보세요.</span></h2>
          </div>
          <div className="max-w-sm">
            <p className="text-sm leading-7 text-slate-300">공고를 고르고 제안서를 검토하는 일부터,<br className="hidden sm:block" />만들던 발표자료를 Gemma와 다듬는 일까지.</p>
            <a href={source} download="AI비드-서비스-소개.mp4" className="mt-3 inline-flex items-center gap-2 text-xs text-[#a4dbd0] underline decoration-[#47796e] underline-offset-4 hover:text-white">소개 영상 다운로드 <span aria-hidden="true">↓</span></a>
          </div>
        </div>

        <div className="overflow-hidden rounded-2xl border border-white/15 bg-[#0d1c26] shadow-[0_24px_80px_-30px_rgba(0,0,0,0.5)]">
          <div className="flex items-center justify-between gap-3 border-b border-white/10 px-4 py-3 text-[11px] sm:px-5">
            <span className="flex items-center gap-2 font-semibold tracking-wide"><span aria-hidden="true" className={`h-1.5 w-1.5 rounded-full ${playing ? "bg-[#8ee0c7]" : "bg-slate-400"}`} />AI비드 · PRODUCT WALKTHROUGH</span>
            <span className="text-slate-400">{time(duration)} <span className="ml-2 hidden sm:inline">한국어 안내 · 자막</span></span>
          </div>
          <div className="relative aspect-video">
            <video
              ref={video}
              aria-label="AI비드 서비스 소개 영상"
              aria-describedby="product-demo-description"
              className="h-full w-full"
              src={source}
              poster={`${storyboard.poster}?v=${storyboard.version}`}
              controls
              playsInline
              preload="none"
              onLoadedMetadata={() => {
                if (pendingSeek.current !== null && video.current) {
                  video.current.currentTime = pendingSeek.current;
                  pendingSeek.current = null;
                }
              }}
              onTimeUpdate={event => setCurrent(event.currentTarget.currentTime)}
              onPlay={() => setPlaying(true)}
              onPause={() => setPlaying(false)}
              onEnded={() => setPlaying(false)}
              onError={() => setError(true)}
            >
              <track kind="captions" src={`${storyboard.captions}?v=${storyboard.version}`} srcLang="ko" label="한국어" default />
              소개 영상을 재생할 수 없습니다. 아래 글로 된 소개를 확인하거나 영상을 다운로드하세요.
            </video>
          </div>
          {error && <p role="alert" className="border-t border-white/10 px-5 py-4 text-sm text-amber-200">영상을 불러오지 못했습니다. <a className="underline" href={source} download>파일 내려받기</a> 또는 아래 글로 된 소개를 이용하세요.</p>}
          <div className="flex flex-wrap items-center justify-between gap-2 border-t border-white/10 px-4 py-3 text-xs text-slate-300 sm:px-5">
            <span>{String(Math.max(0, currentChapter) + 1).padStart(2, "0")} / {String(chapters.length).padStart(2, "0")} <span className="ml-2 text-white">{chapters[Math.max(0, currentChapter)].chapter}</span></span>
            <button type="button" onClick={() => void seek(0)} className="rounded px-2 py-1 text-[#a4dbd0] hover:bg-white/10 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#8ee0c7]">처음부터 보기 ↺</button>
          </div>
        </div>

        <nav aria-label="소개 영상 구간 선택" className="mt-5 grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5">
          {chapters.map((chapter, index) => (
            <button type="button" key={chapter.id} aria-current={index === currentChapter ? "step" : undefined}
              onClick={() => void seek(chapter.start)}
              className={`min-h-16 rounded-lg border px-3 py-3 text-left transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#8ee0c7] ${index === currentChapter ? "border-[#80cbb5]/50 bg-[#24453f]" : "border-white/10 bg-white/[0.025] hover:border-white/30 hover:bg-white/5"}`}>
              <span className="mb-1.5 flex justify-between text-[10px] tabular-nums text-[#a4b9c2]"><span>{String(index + 1).padStart(2, "0")}</span><span>{time(chapter.start)}</span></span>
              <span className="block text-xs font-medium leading-5 text-slate-100">{chapter.chapter}</span>
            </button>
          ))}
        </nav>
        <p id="product-demo-description" className="mt-4 text-[11px] leading-6 text-slate-400">현재 서비스 화면에 가상 회사·프로젝트 자료를 사용한 기능 시연입니다. 작업 시간을 압축해 편집했으며, 생성 결과는 제공한 자료와 모델에 따라 달라집니다.</p>
        <div className="mt-6 flex flex-wrap items-center justify-between gap-5 border-t border-white/10 pt-5">
          <details className="group max-w-2xl text-sm">
            <summary className="cursor-pointer text-slate-300 hover:text-white">글로 된 소개 보기</summary>
            <ol className="mt-5 space-y-4 border-l border-[#47796e] pl-5 text-xs leading-6 text-slate-300">
              {chapters.map(chapter => <li key={chapter.id}><p className="font-semibold text-[#a4dbd0]">{time(chapter.start)} · {chapter.chapter}</p><p className="mt-1">{chapter.narration}</p></li>)}
            </ol>
          </details>
          <div className="flex flex-wrap gap-3 text-xs font-semibold">
            <Link href="/dashBoard/matchBid" className="rounded-lg bg-[#8ee0c7] px-4 py-3 text-[#102630] hover:bg-[#b8f0df]">제안서 작성 시작 →</Link>
            <Link href="/dashBoard/presentations" className="rounded-lg border border-white/20 px-4 py-3 text-white hover:bg-white/10">발표자료 이어 만들기 →</Link>
          </div>
        </div>
      </div>
    </section>
  );
}
