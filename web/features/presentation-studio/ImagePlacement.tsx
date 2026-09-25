"use client";
import { FormEvent } from "react";
import { type Project, type Slide } from "./api";
import { type ReferenceMutate } from "./ReferenceForm";
import { input, button } from "./controls";

export default function ImagePlacement({ project, slide, disabled, mutate }: {
  project: Project; slide?: Slide; disabled: boolean; mutate: ReferenceMutate;
}) {
  const images = project.references?.filter(r => r.metadata.image) || [];
  if (!slide || !images.length) return null;
  const locked = project.protected_slides.includes(slide.number);
  async function insert(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await mutate("edit/", "POST", { ...Object.fromEntries(new FormData(event.currentTarget)), action: "image", base_revision: project.current.id, slide: slide!.number });
  }
  return <details className="mt-5 border-t border-violet-100 pt-4">
    <summary className="cursor-pointer text-sm font-semibold">업로드한 이미지를 {slide.number}쪽에 배치</summary>
    <form key={slide.number} onSubmit={insert} className="mt-3 space-y-3">
      <label className="block text-xs">이미지 선택<select name="reference" required className={input} defaultValue=""><option value="" disabled>이미지 선택</option>{images.map(image => <option key={image.id} value={image.id}>{image.name}</option>)}</select></label>
      <div className="grid grid-cols-3 gap-2">{[["x", "가로 위치", 40], ["y", "세로 위치", 100], ["width", "너비", Math.round(slide.width / 2)]].map(([name, label, value]) => <label key={name} className="text-xs">{label} (pt)<input name={String(name)} type="number" min={name === "width" ? 1 : 0} required defaultValue={value} className={input} /></label>)}</div>
      {locked && <p className="text-xs text-amber-700">이 페이지는 원본 유지 중입니다. 페이지 편집에서 잠금을 해제한 뒤 배치할 수 있습니다.</p>}
      <button disabled={disabled || locked} className={button}>선택한 페이지에 이미지 삽입</button>
    </form>
  </details>;
}
