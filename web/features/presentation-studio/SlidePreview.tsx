"use client";
import { useEffect, useState } from "react";
import { auth, previewURL } from "./api";

export default function SlidePreview({ project, revision, page }: { project: string; revision: number; page: number }) {
  const identity = `${project}/${revision}/${page}`;
  const [preview, setPreview] = useState({ identity: "", url: "", error: "" });
  const url = preview.identity === identity ? preview.url : "";
  const error = preview.identity === identity ? preview.error : "";
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    const controller = new AbortController(); let objectURL = "";
    async function load() {
      try {
        for (let attempt = 0; attempt < 120 && !controller.signal.aborted; attempt++) {
          const response = await fetch(previewURL(project, revision, page) + (retry && attempt === 0 ? "?retry=1" : ""), { headers: auth(), signal: controller.signal });
          if (response.status === 202) { await new Promise(resolve => setTimeout(resolve, 1500)); continue; }
          if (!response.ok) { const data = await response.json().catch(() => ({})); throw new Error(data.error || "미리보기를 만들지 못했습니다. 잠시 후 다시 시도해 주세요."); }
          const blob = await response.blob(); if (controller.signal.aborted) return;
          objectURL = URL.createObjectURL(blob); setPreview({ identity, url: objectURL, error: "" }); return;
        }
        if (!controller.signal.aborted) setPreview({ identity, url: "", error: "미리보기 작업이 오래 걸리고 있습니다. 진행 상태를 확인한 뒤 다시 시도해 주세요." });
      } catch (cause) { if (!controller.signal.aborted) setPreview({ identity, url: "", error: cause instanceof Error ? cause.message : "미리보기 오류" }); }
    }
    void load(); return () => { controller.abort(); if (objectURL) URL.revokeObjectURL(objectURL); };
  }, [project, revision, page, identity, retry]);
  return <div className="flex min-h-48 items-center justify-center overflow-hidden rounded-xl border border-violet-100 bg-white shadow-sm">
    {url ? (
      // Authenticated blob previews cannot use the Next image proxy.
      // eslint-disable-next-line @next/next/no-img-element
      <img className="h-auto w-full" src={url} alt={`${page}페이지 미리보기`} />
    ) : <div className="p-10 text-center text-sm text-slate-500" role="status">{error || "PPTX의 실제 페이지를 불러오는 중…"}{error && <button className="mx-auto mt-3 block text-violet-700 underline" onClick={() => { setPreview({ identity, url: "", error: "" }); setRetry(v => v + 1); }}>미리보기 다시 시도</button>}</div>}
  </div>;
}
