"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { API_BASE_URL } from "@/lib/api";
import TemplateGallery from "@/components/proposal/TemplateGallery";
import type { ProposalTemplateOption } from "@/types/bid";
import { api, auth, type PersonalTemplate, type Project } from "./api";

const input = "w-full rounded-lg border border-violet-200 bg-white px-3 py-2.5 text-sm outline-none focus:border-violet-500";

export default function StudioHome() {
  const router = useRouter();
  const [projects, setProjects] = useState<Project[]>([]);
  const [personal, setPersonal] = useState<PersonalTemplate[]>([]);
  const [library, setLibrary] = useState<ProposalTemplateOption[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [mode, setMode] = useState("upload");
  const [template, setTemplate] = useState("learning_sage");
  const [archived, setArchived] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    let cancelled = false;
    Promise.resolve().then(() => Promise.all([api<{ projects: Project[] }>(`projects/${archived ? "?archived=1" : ""}`), api<{ templates: PersonalTemplate[] }>("templates/"), fetch(`${API_BASE_URL}/api/proposal-templates/`, { headers: auth() }).then(r => r.json())]))
      .then(([p, t, l]) => { if (!cancelled) { setProjects(p.projects); setPersonal(t.templates); setLibrary(l.templates || []); } })
      .catch(e => { if (!cancelled) setError(e.message); });
    return () => { cancelled = true; };
  }, [archived]);
  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError("");
    const form = new FormData(event.currentTarget);
    if (mode !== "upload") form.delete("file");
    if (mode === "library") form.set("template_id", template);
    try { const project = await api<Project>("projects/", "POST", form); router.push(`/dashBoard/presentations/${project.id}`); }
    catch (e) { setError(e instanceof Error ? e.message : "생성 실패"); }
    finally { setBusy(false); }
  }
  return <div className="space-y-7 pb-10">
    <header className="flex flex-wrap items-start justify-between gap-4">
      <div><p className="text-xs font-semibold tracking-widest text-violet-600">PRESENTATION STUDIO</p><h1 className="mt-2 text-3xl font-bold tracking-tight text-slate-900">발표자료 작업실</h1><p className="mt-3 text-sm leading-6 text-slate-600">수업, 프로젝트 발표, 보고서. 나의 자료와 양식으로 Gemma4와 함께 만드세요.</p></div>
      <button onClick={() => setShowCreate(v => !v)} className="rounded-xl bg-violet-700 px-5 py-3 text-sm font-semibold text-white hover:bg-violet-800">{showCreate ? "닫기" : "+ 새 발표자료"}</button>
    </header>
    {error && <p role="alert" className="rounded-lg bg-rose-50 p-4 text-sm text-rose-800">{error} <Link href="/login" className="underline">로그인</Link></p>}
    {showCreate && <form onSubmit={create} className="space-y-5 rounded-2xl border border-violet-200 bg-white p-5 shadow-sm sm:p-7">
      <h2 className="text-lg font-bold">어디서 시작할까요?</h2>
      <div className="flex flex-wrap gap-2">{[["upload", "작업 중인 PPTX 이어서"], ["library", "기본 양식에서 새로"], ["personal", "저장한 내 양식"]].map(([value, label]) => <button type="button" key={value} aria-pressed={mode === value} onClick={() => setMode(value)} className={`rounded-lg border px-4 py-3 text-sm ${mode === value ? "border-violet-500 bg-violet-50 font-semibold text-violet-800" : "border-slate-200"}`}>{label}</button>)}</div>
      {mode === "upload" && <label className="block rounded-xl border border-dashed border-violet-300 bg-violet-50/50 p-5 text-sm"><span className="mb-3 block font-semibold">희망하는 양식 또는 작성 중인 PPTX 업로드</span><input name="file" type="file" accept=".pptx" required className="w-full" /><span className="mt-3 block text-xs text-slate-500">1~80쪽 · 40MB 이하. 업로드 후 그대로 유지할 페이지를 선택합니다. 원본은 첫 버전으로 보관합니다.</span></label>}
      {mode === "library" && <div className="space-y-4"><TemplateGallery templates={library} selectedTemplateId={template} recommendedTemplateId="" recommendationReason="" onSelect={setTemplate} /><label className="block max-w-xs text-sm">처음 가져올 페이지 수<input name="initial_pages" type="number" min="1" max={library.find(t => t.id === template)?.slide_count || 20} defaultValue="5" className={input} /></label></div>}
      {mode === "personal" && <label className="block text-sm">내가 저장한 양식<select name="personal_template" required className={input} defaultValue=""><option value="" disabled>양식 선택</option>{personal.map(t => <option key={t.id} value={t.id}>{t.name} · {t.slide_count}쪽</option>)}</select>{!personal.length && <span className="mt-2 block text-xs text-slate-500">PPTX를 올린 뒤 작업실에서 ‘내 양식으로 저장’을 누르면 여기에 나타납니다.</span>}</label>}
      <div className="grid gap-4 sm:grid-cols-2"><label className="text-sm">발표자료 이름<input name="title" required maxLength={200} placeholder="예: 파이썬 팀 프로젝트 발표" className={input} /></label><label className="text-sm">발표 대상 <span className="text-slate-400">선택</span><input name="audience" maxLength={300} placeholder="예: 학원 수강생과 강사" className={input} /></label></div>
      <label className="block text-sm">작성 instruction <span className="text-slate-400">선택 · 나중에 대화로 정해도 됩니다</span><textarea name="instruction" rows={4} maxLength={16000} placeholder="과제 지침을 붙여넣거나 원하는 구성·분량·말투를 직접 적으세요." className={input} /></label>
      <button disabled={busy || (mode === "personal" && !personal.length)} className="rounded-lg bg-violet-700 px-6 py-3 text-sm font-semibold text-white disabled:opacity-40">{busy ? "원본을 확인하고 있습니다…" : "작업실 만들기"}</button>
    </form>}
    <section><div className="mb-4 flex items-center justify-between"><h2 className="font-bold">{archived ? "보관한 발표자료" : "나의 발표자료"}</h2><button className="text-sm text-violet-700" onClick={() => setArchived(v => !v)}>{archived ? "진행 중 보기" : "보관함 보기"}</button></div>
      {!projects.length && <div className="rounded-2xl border border-dashed border-violet-200 bg-white/70 px-6 py-14 text-center"><p className="font-semibold text-slate-700">{archived ? "보관한 자료가 없습니다." : "만들던 5쪽도, 첫 아이디어도 여기서 이어가세요."}</p><p className="mt-3 text-sm text-slate-500">입찰 프로젝트와 섞이지 않는 독립된 발표자료 공간입니다.</p></div>}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">{projects.map(p => <Link key={p.id} href={`/dashBoard/presentations/${p.id}`} className="rounded-2xl border border-violet-100 bg-white p-5 shadow-sm transition hover:border-violet-300 hover:shadow-md"><div className="flex justify-between text-xs text-violet-600"><span>PPTX · {p.current?.slide_count || 0}쪽</span><span>v{p.current?.number || 1}</span></div><h3 className="mt-4 text-lg font-bold text-slate-900">{p.title}</h3><p className="mt-2 line-clamp-2 text-sm leading-6 text-slate-500">{p.audience || p.instruction || "원하는 방향을 Gemma4와 이야기해 보세요."}</p><p className="mt-5 text-xs text-slate-400">{new Date(p.updated_at).toLocaleString("ko-KR")}</p></Link>)}</div>
    </section>
  </div>;
}
