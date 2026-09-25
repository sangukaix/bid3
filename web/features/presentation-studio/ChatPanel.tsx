"use client";
import { FormEvent, useRef, useState, useEffect } from "react";
import { type Project } from "./api";
import { input, button, primary } from "./controls";

export default function ChatPanel({ project, page, disabled, mutate }: { project: Project; page: number; disabled: boolean; mutate: (path: string, method: string, data?: object | FormData) => Promise<boolean> }) {
  const [mode, setMode] = useState("discuss");
  const [count, setCount] = useState(3);
  const [text, setText] = useState("");
  const scrollArea = useRef<HTMLDivElement>(null);
  const messages = project.messages || [];
  useEffect(() => { const area = scrollArea.current; if (area) area.scrollTop = area.scrollHeight; }, [messages.length]);
  async function send(event: FormEvent) {
    event.preventDefault();
    if (await mutate("chat/", "POST", { message: text, mode, count, slide: page })) setText("");
  }
  return <aside className="flex min-h-[600px] flex-col rounded-2xl border border-violet-200 bg-white xl:sticky xl:top-5 xl:max-h-[calc(100vh-40px)]">
    <div className="border-b border-violet-100 p-4"><h2 className="font-bold text-violet-900">Gemma와 함께 작성</h2></div>
    <div ref={scrollArea} className="min-h-0 flex-1 space-y-4 overflow-y-auto p-4" aria-live="polite">
      {messages.map(m => {
        const plan = m.plan || {};
        const changed = !!(plan.changes?.length || plan.additions?.length || plan.rewrite_slides?.length);
        const stale = !!plan.base_revision && plan.base_revision !== project.current.id;
        return <article key={m.id} className={`rounded-xl p-3 text-sm ${m.role === "user" ? "ml-5 bg-violet-100" : "border border-slate-200 bg-slate-50"}`}>
          <p className="mb-2 text-xs font-bold text-violet-800">{m.role === "user" ? "나" : "Gemma"}</p><div className="whitespace-pre-wrap break-words leading-6">{m.content}</div>
          {!!plan.questions?.length && <div className="mt-3 rounded-lg bg-amber-50 p-3"><p className="font-semibold text-amber-900">확인이 필요해요</p><ul className="mt-2 list-disc space-y-1 pl-4">{plan.questions.map((q, i) => <li key={i}>{q}</li>)}</ul><p className="mt-2 text-xs text-slate-500">아래에 답변하고 원하는 작성 모드를 선택해 다시 보내 주세요.</p></div>}
          {!!plan.image_requests?.length && <div className="mt-3 rounded-lg bg-sky-50 p-3"><p className="font-semibold">필요한 이미지·샘플</p>{plan.image_requests.map((r, i) => <p key={i} className="mt-2">{r}</p>)}<button className="mt-2 text-xs text-violet-700 underline" onClick={() => setText(`이미지 방향에 대한 답변: ${plan.image_requests?.join(" / ")}\n`)}>답변 작성</button></div>}
          {changed && <details open className="mt-3"><summary className="cursor-pointer font-semibold">적용할 작성안</summary>
            {plan.changes?.map((c, i) => <div key={i} className="mt-2"><p className="font-medium">{c.slide}쪽 · {c.edits.length}개 텍스트 수정</p>{c.edits.map((e, j) => <p key={j} className="mt-1 whitespace-pre-wrap rounded bg-white p-2 text-xs leading-5">{e.text}</p>)}</div>)}
            {plan.additions?.map((a, i) => <p key={i} className="mt-2 text-xs leading-5">+ {a.title} <span className="text-slate-400">({a.template_slide}쪽 디자인)</span><br />{a.brief}</p>)}
            {!!plan.rewrite_slides?.length && <p className="mt-2 text-xs">내용 재작성: {plan.rewrite_slides.join(", ")}쪽. 잠긴 페이지는 유지합니다.</p>}
          </details>}
          {!!plan.sources?.length && <p className="mt-3 text-xs text-slate-500">참고한 자료: {plan.sources.map(s => s.name).join(", ")}</p>}
          {!!plan.omitted_reference_count && <p className="mt-2 text-xs text-amber-700">입력 길이 제한으로 {plan.omitted_reference_count}개 자료가 제외되었습니다. 필요 없는 자료를 끄고 다시 요청해 주세요.</p>}
          {changed && <div className="mt-3">{m.applied_revision ? <span className="text-xs text-emerald-700">수정본에 적용됨</span> : stale ? <span className="text-xs text-amber-700">파일이 변경되어 새 작성안이 필요합니다.</span> : <button disabled={disabled || !!plan.questions?.length} className={primary} onClick={() => void mutate(`plans/${m.id}/apply/`, "POST")}>이 작성안 적용</button>}</div>}
        </article>;
      })}
    </div>
    <form onSubmit={send} className="space-y-3 border-t border-violet-100 p-4">
      <label className="block text-xs font-semibold">작업 범위<select className={input} value={mode} onChange={e => setMode(e.target.value)}><option value="discuss">방향·구성 함께 의논</option><option value="revise">현재 {page}쪽 수정</option><option value="continue">기존 페이지 유지하고 이어 만들기</option><option value="rewrite">잠금 해제한 모든 페이지 재작성</option></select></label>
      {mode === "continue" && <label className="flex items-center gap-3 text-xs">추가 장수<input type="number" min={1} max={10} value={count} onChange={e => setCount(Number(e.target.value))} className={`${input} max-w-20`} /></label>}
      <label className="block text-xs font-semibold">요청·답변<textarea value={text} onChange={e => setText(e.target.value)} rows={4} maxLength={8000} required className={input} placeholder="원하는 내용이나 질문에 대한 답변을 적어 주세요." /></label>
      {!project.template_confirmed && <p className="text-xs text-amber-700">왼쪽에서 양식과 유지할 페이지를 먼저 확인하세요.</p>}
      <button className={primary} disabled={disabled || !project.template_confirmed || !text.trim() || (mode === "revise" && project.protected_slides.includes(page))}>Gemma에게 보내기</button>
      <button type="button" className={`${button} ml-2`} onClick={() => setText("이 발표자료에서 아직 정해야 할 내용과 필요한 참고자료를 먼저 질문해 줘.")}>먼저 질문받기</button>
    </form>
  </aside>;
}
