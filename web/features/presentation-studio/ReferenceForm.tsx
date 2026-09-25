"use client";
import { FormEvent, useState } from "react";
import { type Capabilities } from "./api";
import { input, primary } from "./controls";

export type ReferenceKind = "url" | "upload" | "image" | "text" | "path";
export type ReferenceMutate = (path: string, method: string, data?: object | FormData) => Promise<boolean>;

export default function ReferenceForm({ kind, capabilities, disabled, mutate }: {
  kind: ReferenceKind; capabilities?: Capabilities; disabled: boolean; mutate: ReferenceMutate;
}) {
  const [saved, setSaved] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setSaved(false);
    const form = event.currentTarget;
    const data = new FormData(form);
    data.set("kind", kind === "image" ? "upload" : kind);
    if (await mutate("references/", "POST", data)) { form.reset(); setSaved(true); }
  }
  return <form onSubmit={submit} onChange={() => setSaved(false)} className="space-y-3">
    {kind === "upload" || kind === "image" ? <label className="block text-sm font-medium">
      {kind === "image" ? "참고 이미지 선택" : "참고자료 파일 선택"}
      <input name="file" type="file" required disabled={disabled} accept={kind === "image" ? ".png,.jpg,.jpeg" : ".pdf,.docx,.pptx,.txt,.md,.csv,.json,.py,.js,.jsx,.ts,.tsx,.html,.css,.sql,.yaml,.yml"} className="mt-3 block w-full rounded-lg border border-violet-100 bg-white p-3 text-xs file:mr-3 file:rounded-md file:border-0 file:bg-violet-100 file:px-3 file:py-2 file:text-violet-900" />
      <span className="mt-2 block text-xs font-normal text-slate-500">{kind === "image" ? "PNG·JPG · 16MB 이하. Gemma가 다음 요청에서 참고 이미지로 분석합니다." : "PDF·Word·PPTX·텍스트·코드 · 16MB 이하"}</span>
    </label> : <>
      <label className="block text-sm">자료 이름<input name="name" required maxLength={250} className={input} /></label>
      {kind === "text" ? <label className="block text-sm">자료 내용<textarea name="text" rows={7} required maxLength={200000} className={input} /></label> : <label className="block text-sm">{kind === "url" ? "참고할 웹 주소" : "서버 PC의 절대 경로"}<input name="locator" required type={kind === "url" ? "url" : "text"} maxLength={2048} className={input} placeholder={kind === "url" ? "https://" : "D:\\projects\\my-project"} /></label>}
    </>}
    {kind === "url" && <p className="text-xs text-slate-500">공개 웹 문서의 본문을 읽습니다. 로그인이 필요한 자료는 파일로 업로드해 주세요.</p>}
    {kind === "path" && <p className="text-xs leading-5 text-slate-500">{capabilities?.path_note} 소스 최대 80개·3MB를 읽습니다.</p>}
    <button disabled={disabled} className={primary}>{kind === "url" ? "URL 추가" : kind === "image" ? "이미지 업로드" : kind === "upload" ? "참고자료 업로드" : "자료 추가"}</button>
    {saved && <p role="status" className="text-sm text-emerald-700">추가했습니다. ‘지침·참고자료’에서 확인할 수 있습니다.</p>}
  </form>;
}
