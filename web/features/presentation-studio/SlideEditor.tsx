"use client";
import { FormEvent, useState } from "react";
import { type Project, type Slide } from "./api";
import { input, button, primary } from "./controls";

export default function SlideEditor({ slide, project, disabled, mutate }: { slide: Slide; project: Project; disabled: boolean; mutate: (path: string, method: string, data?: object | FormData) => Promise<boolean> }) {
  const [target, setTarget] = useState(slide.elements[0]?.target || "");
  const selected = slide.elements.find(e => e.target === target);
  const images = project.references?.filter(r => r.metadata.image) || [];
  const locked = project.protected_slides.includes(slide.number);
  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const data = new FormData(event.currentTarget);
    const edit: Record<string, unknown> = { target, text: String(data.get("text") || "") };
    if (data.get("font_size")) edit.font_size = Number(data.get("font_size"));
    if (data.get("color")) edit.color = String(data.get("color")).replace("#", "");
    if (data.get("bold") !== "") edit.bold = data.get("bold") === "true";
    await mutate("edit/", "POST", { base_revision: project.current.id, slide: slide.number, edits: [edit] });
  }
  async function image(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const data = Object.fromEntries(new FormData(event.currentTarget));
    await mutate("edit/", "POST", { ...data, action: "image", base_revision: project.current.id, slide: slide.number });
  }
  return <div className="space-y-4">
    {locked && <p className="rounded-lg bg-amber-50 p-3 text-sm text-amber-800">원본 유지 중인 페이지입니다. 수정하려면 위의 ‘원본 유지’ 체크를 해제하세요.</p>}
    <details open><summary className="cursor-pointer text-sm font-semibold">텍스트 직접 편집</summary>
      {!slide.elements.length ? <p className="my-3 text-sm text-slate-500">편집할 텍스트가 없습니다. 이미지로 구성된 페이지는 새 디자인 페이지를 복제해 사용하세요.</p> : <>
        <label className="mt-3 block text-xs">텍스트 상자 / 표 셀<select value={target} onChange={e => setTarget(e.target.value)} className={input}>{slide.elements.map((e, i) => <option key={e.target} value={e.target}>{e.kind === "cell" ? "표 셀" : "텍스트"} {i + 1} · {e.text.slice(0, 55) || "빈 텍스트"}</option>)}</select></label>
        {selected && <form key={target} onSubmit={save} className="mt-3 space-y-3"><label className="block text-xs">내용<textarea name="text" rows={5} maxLength={5000} defaultValue={selected.text} className={input} /></label><div className="grid gap-2 sm:grid-cols-3">
          <label className="text-xs">글자 크기 (선택)<input name="font_size" type="number" min={8} max={120} step={0.5} placeholder={`현재 ${selected.font_size}pt`} className={input} /></label>
          <label className="text-xs">색상 (선택)<input name="color" placeholder="#243456" pattern="#?[0-9a-fA-F]{6}" className={input} /></label>
          <label className="text-xs">굵기<select name="bold" className={input}><option value="">원래대로</option><option value="true">굵게</option><option value="false">보통</option></select></label>
        </div><button className={primary} disabled={disabled || locked}>텍스트 저장</button><p className="text-xs leading-5 text-slate-400">선택한 상자의 기존 위치·배경은 유지합니다. 텍스트를 바꾸면 상자 안의 글자 서식은 첫 문단 기준으로 통일됩니다. 저장 후 미리보기에서 넘침을 확인하세요.</p></form>}
      </>}
    </details>
    <details className="border-t border-slate-100 pt-3"><summary className="cursor-pointer text-sm font-semibold">업로드 이미지 넣기</summary>
      <p className="my-3 text-xs leading-5 text-slate-500">참고자료에 PNG/JPG를 올린 뒤 선택하세요. 위치는 슬라이드 왼쪽 위 기준 pt이며, 비율을 유지해 삽입합니다. 페이지 크기: {Math.round(slide.width)} × {Math.round(slide.height)}pt.</p>
      <form onSubmit={image} className="space-y-3"><label className="block text-xs">이미지<select name="reference" required className={input} defaultValue=""><option value="" disabled>업로드 이미지 선택</option>{images.map(i => <option key={i.id} value={i.id}>{i.name}</option>)}</select></label><div className="grid grid-cols-3 gap-2">{[["x", "가로 위치", 40], ["y", "세로 위치", 160], ["width", "이미지 너비", 250]].map(([name, label, value]) => <label key={name} className="text-xs">{label}<input name={String(name)} type="number" min={name === "width" ? 1 : 0} required defaultValue={value} className={input} /></label>)}</div><button className={button} disabled={disabled || locked || !images.length}>이미지 삽입</button></form>
    </details>
  </div>;
}
