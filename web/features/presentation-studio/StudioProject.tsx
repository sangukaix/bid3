"use client";
import Link from "next/link";
import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { api, download, type Capabilities, type Project } from "./api";
import { input, button, primary } from "./controls";
import SlideDeck from "./SlideDeck";
import SlideEditor from "./SlideEditor";
import ReferencePanel from "./ReferencePanel";
import ChatPanel from "./ChatPanel";

export default function StudioProject({ id }: { id: string }) {
  const [project, setProject] = useState<Project>();
  const [capabilities, setCapabilities] = useState<Capabilities>();
  const [page, setPage] = useState(1);
  const [tab, setTab] = useState("pages");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [saveTemplate, setSaveTemplate] = useState(false);
  const sequence = useRef(0);
  const root = `projects/${id}/`;
  const refresh = useCallback(async () => {
    const current = ++sequence.current;
    const result = await api<Project>(root);
    if (current === sequence.current) setProject(result);
  }, [root]);
  useEffect(() => {
    let alive = true;
    let timer: ReturnType<typeof setTimeout>;
    async function poll() {
      try { await refresh(); } catch (e) { if (alive) setError(e instanceof Error ? e.message : "작업실을 불러오지 못했습니다."); }
      if (alive) timer = setTimeout(poll, 3500);
    }
    void poll();
    void api<Capabilities>("capabilities/").then(v => { if (alive) setCapabilities(v); }).catch(() => {});
    return () => { alive = false; clearTimeout(timer); };
  }, [refresh]);
  async function mutate(path: string, method: string, data?: object | FormData) {
    setBusy(true); setError(""); setNotice("");
    try { await api(root + path, method, data); await refresh(); return true; }
    catch (e) { setError(e instanceof Error ? e.message : "저장하지 못했습니다."); return false; }
    finally { setBusy(false); }
  }
  async function getFile(path: string, filename: string) {
    try { await download(root + path, filename); } catch (e) { setError(e instanceof Error ? e.message : "다운로드 실패"); }
  }
  async function template(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const name = new FormData(event.currentTarget).get("name"); setBusy(true); setError("");
    try { await api("templates/", "POST", { project: id, name }); setSaveTemplate(false); setNotice("내 양식으로 저장했습니다. 새 발표자료에서 ‘저장한 내 양식’을 선택해 다시 사용할 수 있습니다."); }
    catch (e) { setError(e instanceof Error ? e.message : "양식 저장 실패"); } finally { setBusy(false); }
  }
  if (!project) return <div className="rounded-2xl bg-white p-8">{error ? <p role="alert" className="text-rose-700">{error} <Link className="underline" href="/login">로그인</Link></p> : "발표자료를 불러오는 중…"}</div>;
  const slides = project.current.slides || [];
  const currentPage = Math.min(page, slides.length);
  const slide = slides[currentPage - 1];
  const activeJob = project.jobs?.find(j => ["queued", "running"].includes(j.status));
  const lastJob = project.jobs?.find(j => j.kind !== "preview") || project.jobs?.[0];
  const disabled = busy || !!activeJob;
  const locked = project.protected_slides.includes(currentPage);
  async function pageAction(action: string, extra = {}) {
    return mutate("edit/", "POST", { action, slide: currentPage, base_revision: project!.current.id, ...extra });
  }
  async function move(direction: number) {
    const target = currentPage + direction;
    const order = slides.map(s => s.number);
    [order[currentPage - 1], order[target - 1]] = [order[target - 1], order[currentPage - 1]];
    if (await pageAction("order", { order })) setPage(target);
  }
  return <div className="space-y-5 pb-10">
    <header className="space-y-4"><Link href="/dashBoard/presentations" className="text-xs font-semibold text-violet-700">← 발표자료 작업실</Link><div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-xs text-violet-600">{capabilities?.model || "Gemma4"} · 로컬 AI · v{project.current.number} · {slides.length}쪽</p><h1 className="mt-2 text-2xl font-bold tracking-tight">{project.title}</h1></div><div className="flex flex-wrap gap-2"><button className={button} onClick={() => setSaveTemplate(v => !v)}>내 양식으로 저장</button><button className={primary} onClick={() => void getFile(`revisions/${project.current.id}/download/`, `${project.title}.pptx`)}>PPTX 다운로드</button></div></div></header>
    {error && <div role="alert" className="flex justify-between gap-3 rounded-xl bg-rose-50 p-4 text-sm text-rose-800"><span>{error}</span><button onClick={() => setError("")} aria-label="오류 닫기">×</button></div>}
    {notice && <p role="status" className="rounded-xl bg-emerald-50 p-4 text-sm text-emerald-800">{notice}</p>}
    {saveTemplate && <form onSubmit={template} className="flex flex-wrap gap-3 rounded-xl border border-violet-200 bg-white p-4"><label className="min-w-48 flex-1 text-xs">저장할 내 양식 이름<input className={input} name="name" required maxLength={200} defaultValue={`${project.title} 양식`} /></label><button disabled={disabled} className={primary}>현재 파일과 유지 설정 저장</button><p className="w-full text-xs text-slate-500">현재 텍스트·이미지까지 포함하는 개인 양식입니다. 내 계정에서만 다시 선택할 수 있습니다.</p></form>}
    {activeJob && <div role="status" className="flex items-center justify-between gap-3 rounded-xl border border-violet-200 bg-violet-100 p-4 text-sm text-violet-900"><span className="animate-pulse">{activeJob.progress || "작업 준비 중…"} · 로컬 모델은 자료량에 따라 몇 분 걸릴 수 있습니다.</span><button disabled={busy} className={button} onClick={() => void mutate(`jobs/${activeJob.id}/cancel/`, "POST")}>작업 취소</button></div>}
    {!activeJob && lastJob?.status === "failed" && <p role="alert" className="rounded-xl bg-amber-50 p-4 text-sm text-amber-900">{lastJob.error} 새 요청을 보내거나 미리보기를 재시도할 수 있습니다.</p>}
    <div className="grid items-start gap-5 xl:grid-cols-[minmax(0,1fr)_360px] 2xl:grid-cols-[minmax(0,1fr)_400px]">
      <section className="min-w-0 space-y-4">
        <div className="flex flex-wrap gap-1 rounded-xl border border-violet-100 bg-white p-1.5">{[["pages", "페이지·디자인"], ["sources", `지침·참고자료 ${project.references?.length || 0}`], ["history", "버전·작업 연결"]].map(([value, label]) => <button key={value} onClick={() => setTab(value)} aria-pressed={tab === value} className={`rounded-lg px-4 py-2.5 text-sm ${tab === value ? "bg-violet-100 font-bold text-violet-900" : "text-slate-500"}`}>{label}</button>)}</div>
        {tab === "pages" && <>
          {!project.template_confirmed && <div className="space-y-3 rounded-xl border border-amber-200 bg-amber-50 p-4"><h2 className="text-sm font-bold text-amber-950">이 양식으로 이어 작성할까요?</h2><p className="text-sm leading-6 text-amber-900">페이지를 확인하고, 손대지 않을 페이지에 ‘원본 유지’를 켜 주세요. 새 페이지는 기존 페이지의 디자인을 복제해 만듭니다. 선택은 나중에도 바꿀 수 있습니다.</p><button className={primary} disabled={disabled} onClick={() => void mutate("", "PATCH", { template_confirmed: true })}>현재 양식과 유지 설정으로 시작</button></div>}
          <SlideDeck project={id} revision={project.current.id} slides={slides} page={currentPage} protectedSlides={project.protected_slides} onSelect={setPage} />
          <details className="rounded-2xl border border-violet-100 bg-white p-4 sm:p-5">
            <summary className="cursor-pointer text-sm font-bold text-violet-900">{currentPage}쪽 편집 · 원본 유지 설정</summary>
            <div className="mt-4">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3"><label className="flex min-w-0 flex-1 items-center gap-2 text-sm">페이지<select className={`${input} max-w-sm`} value={currentPage} onChange={e => setPage(Number(e.target.value))}>{slides.map(s => <option key={s.number} value={s.number}>{project.protected_slides.includes(s.number) ? "🔒 " : ""}{s.number}. {s.title.slice(0, 50) || "제목 없음"}</option>)}</select></label><label className="flex items-center gap-2 text-sm font-semibold text-violet-800"><input type="checkbox" checked={locked} disabled={disabled} onChange={e => void mutate("", "PATCH", { protected_slides: e.target.checked ? [...project.protected_slides, currentPage] : project.protected_slides.filter(n => n !== currentPage) })} />원본 유지</label></div>
            <div className="mb-3 flex flex-wrap items-center gap-3 text-xs text-slate-500"><span>유지 페이지: {project.protected_slides.length ? project.protected_slides.join(", ") : "없음"}</span><button disabled={disabled} className="text-violet-700 disabled:opacity-40" onClick={() => void mutate("", "PATCH", { protected_slides: slides.map(s => s.number) })}>전체 원본 유지</button><button disabled={disabled} className="text-violet-700 disabled:opacity-40" onClick={() => void mutate("", "PATCH", { protected_slides: [] })}>전체 잠금 해제</button></div>
            <div className="my-4 flex flex-wrap gap-2"><button className={button} disabled={disabled || currentPage <= 1} onClick={() => void move(-1)}>페이지 순서 앞으로</button><button className={button} disabled={disabled || currentPage >= slides.length} onClick={() => void move(1)}>페이지 순서 뒤로</button></div>
            <div className="mb-5 flex flex-wrap gap-2 border-b border-slate-100 pb-4"><button className={button} disabled={disabled || slides.length >= 80} onClick={async () => { if (await pageAction("clone")) setPage(slides.length + 1); }}>이 디자인으로 끝에 한 장 복제</button><button className={button} disabled={disabled || locked || slides.length <= 1} onClick={() => { if (window.confirm(`${currentPage}쪽을 삭제할까요? 이전 버전에는 남아 있습니다.`)) void pageAction("delete"); }}>현재 페이지 삭제</button></div>
            {slide && <SlideEditor key={`${project.current.id}-${currentPage}`} slide={slide} project={project} disabled={disabled} mutate={mutate} />}
            </div>
          </details>
        </>}
        {tab === "sources" && <div className="space-y-7 rounded-2xl border border-violet-100 bg-white p-5">
          <form key={project.id} className="space-y-3" onSubmit={async e => { e.preventDefault(); const data = Object.fromEntries(new FormData(e.currentTarget)); if (await mutate("", "PATCH", data)) setNotice("작성 지침을 저장했습니다. 다음 대화부터 사용합니다."); }}><h2 className="font-bold">발표 목적과 작성 지침</h2><label className="block text-xs">발표자료 이름<input name="title" required maxLength={200} defaultValue={project.title} className={input} /></label><label className="block text-xs">발표 대상 (선택)<input name="audience" maxLength={300} defaultValue={project.audience} className={input} /></label><label className="block text-xs">Instruction (선택)<textarea name="instruction" rows={7} maxLength={16000} defaultValue={project.instruction} className={input} placeholder="정해진 지침이 없어도 됩니다. 구성·말투·분량을 적거나 대화에서 함께 정하세요." /></label><button className={primary} disabled={disabled}>지침 저장</button></form>
          <div className="border-t border-slate-100 pt-6"><ReferencePanel project={project} capabilities={capabilities} disabled={disabled} mutate={mutate} /></div>
        </div>}
        {tab === "history" && <div className="space-y-6 rounded-2xl border border-violet-100 bg-white p-5">
          <div><h2 className="font-bold">원본과 수정 이력</h2><p className="mt-2 text-xs leading-5 text-slate-500">복원도 새 버전으로 저장합니다. 현재 잠긴 페이지가 달라지는 복원은 잠금을 먼저 해제해야 합니다.</p></div>
          {project.revisions?.map(r => <div key={r.id} className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-3"><div><p className="text-sm font-semibold">v{r.number} · {r.label} {r.id === project.current.id ? "(현재)" : ""}</p><p className="mt-1 text-xs text-slate-400">{r.slide_count}쪽 · {new Date(r.created_at).toLocaleString("ko-KR")}</p></div><div className="flex gap-2"><button className={button} onClick={() => void getFile(`revisions/${r.id}/download/`, `${project.title}-v${r.number}.pptx`)}>다운로드</button><button className={button} disabled={disabled || r.id === project.current.id} onClick={() => { if (window.confirm(`v${r.number} 내용으로 복원할까요?`)) void mutate(`revisions/${r.id}/restore/`, "POST", { base_revision: project.current.id }); }}>복원</button></div></div>)}
          <div className="rounded-xl bg-violet-50 p-4"><h3 className="text-sm font-bold">Codex에서 프로젝트를 더 검토하려면</h3><p className="my-3 text-xs leading-6 text-slate-600">PPTX 경로, 참고자료와 대화를 작업 설명으로 내보냅니다. 이 설명을 Codex에 전달하면 같은 자료를 바탕으로 이어 작업할 수 있습니다. 웹 화면이 Codex·VS Code를 직접 제어하지는 않습니다.</p><button className={button} onClick={() => void getFile("handoff/", "presentation-handoff.md")}>Codex 전달용 작업 설명 다운로드</button></div>
          <button className={button} disabled={disabled} onClick={() => void mutate("", "PATCH", { archived: !project.archived })}>{project.archived ? "보관함에서 꺼내기" : "이 발표자료 보관하기"}</button>
        </div>}
      </section>
      <ChatPanel project={project} page={currentPage} disabled={disabled} mutate={mutate} />
    </div>
  </div>;
}
