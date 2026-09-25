"use client";
import { FormEvent, useState } from "react";
import { type Capabilities, type Project } from "./api";
import { input, button, primary } from "./controls";

type Props = { project: Project; capabilities?: Capabilities; disabled: boolean; mutate: (path: string, method: string, data?: object | FormData) => Promise<boolean> };
export default function ReferencePanel({ project, capabilities, disabled, mutate }: Props) {
  const [kind, setKind] = useState("upload");
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = event.currentTarget;
    const data = new FormData(form); data.set("kind", kind);
    if (await mutate("references/", "POST", data)) form.reset();
  }
  return <div className="space-y-5">
    <div><h2 className="font-bold">참고자료</h2><p className="mt-2 text-sm leading-6 text-slate-500">작성 지침, 프로젝트 코드, 웹 문서와 샘플 이미지를 모으세요. 웹·PC 경로는 AI 요청 때 다시 읽고, 요청에 관련된 발췌를 사용합니다.</p></div>
    <form onSubmit={submit} className="space-y-3 rounded-xl bg-violet-50 p-4">
      <label className="block text-sm">추가 방법<select className={input} value={kind} onChange={e => setKind(e.target.value)}><option value="upload">파일 업로드</option><option value="text">직접 입력 / 붙여넣기</option><option value="url">웹 링크</option>{capabilities?.local_paths_allowed && <option value="path">서버 PC 파일 / 프로젝트 폴더 경로</option>}</select></label>
      {kind === "upload" ? <label className="block text-sm">참고 파일<input name="file" type="file" required accept=".pdf,.docx,.pptx,.txt,.md,.csv,.json,.py,.js,.jsx,.ts,.tsx,.html,.css,.sql,.yaml,.yml,.png,.jpg,.jpeg" className="mt-2 w-full text-xs" /><span className="mt-2 block text-xs leading-5 text-slate-500">16MB 이하. PDF·Word·PPTX·텍스트·코드·PNG/JPG. 스캔 PDF는 텍스트가 없으면 이미지로 올려 주세요.</span></label> : <>
        <label className="block text-sm">자료 이름<input name="name" required maxLength={250} className={input} placeholder="예: 강사님 과제 지침" /></label>
        {kind === "text" ? <label className="block text-sm">자료 내용<textarea name="text" rows={7} required maxLength={200000} className={input} /></label> : <label className="block text-sm">{kind === "url" ? "공개 웹 주소" : "절대 경로"}<input name="locator" required type={kind === "url" ? "url" : "text"} maxLength={2048} className={input} placeholder={kind === "url" ? "https://example.com/document" : "D:\\projects\\my-project"} /></label>}
      </>}
      {kind === "path" && <p className="text-xs leading-5 text-slate-600">{capabilities?.path_note} 소스 최대 80개·3MB를 읽으며 비밀 설정과 의존성 폴더는 제외합니다. 실행 결과가 필요하면 로그나 화면도 올려 주세요.</p>}
      {kind === "url" && <p className="text-xs text-slate-500">공개 문서의 본문을 읽습니다. 로그인 전용·스크립트로만 표시되는 페이지는 파일이나 텍스트로 올려 주세요.</p>}
      <button disabled={disabled} className={primary}>자료 추가</button>
    </form>
    {!capabilities?.local_paths_allowed && <p className="text-xs text-slate-500">PC 경로 읽기는 서버 관리자 계정에서 제공합니다. 다른 PC의 자료는 파일로 올려 주세요.</p>}
    {project.references?.map(r => <article key={r.id} className="space-y-3 rounded-xl border border-slate-200 p-4">
      <div className="flex items-start justify-between gap-2"><label className="flex min-w-0 items-start gap-2 text-sm font-semibold"><input type="checkbox" className="mt-1" checked={r.enabled} disabled={disabled} onChange={e => void mutate(`references/${r.id}/`, "PATCH", { enabled: e.target.checked })} /><span className="break-all">{r.name}</span></label><span className="text-xs text-slate-400">{r.kind}</span></div>
      {r.locator && <p className="break-all text-xs text-slate-500">{r.locator}</p>}
      <p className="text-xs text-slate-500">{r.text_length.toLocaleString()}자 · {new Date(r.updated_at).toLocaleString("ko-KR")}{r.metadata.vision_pending ? " · 다음 AI 요청에서 이미지 분석" : ""}</p>
      {(r.metadata.empty || (!r.text_length && !r.metadata.image)) && <p className="text-xs text-amber-700">읽을 수 있는 본문이 없습니다. 텍스트 또는 이미지를 추가해 주세요.</p>}
      {r.metadata.truncated && <p className="text-xs text-amber-700">크기 제한으로 자료 일부만 읽었습니다. 필요한 부분을 나눠 추가해 주세요.</p>}
      <details className="text-xs text-slate-600"><summary className="cursor-pointer">읽은 내용 확인{r.metadata.files ? ` · ${r.metadata.files.length}개 파일` : ""}</summary>{r.metadata.files && <p className="my-2 break-all">{r.metadata.files.join(", ")}</p>}<pre className="mt-2 max-h-56 overflow-auto whitespace-pre-wrap break-words font-sans leading-5">{r.excerpt || "이미지 분석을 기다리고 있습니다."}</pre></details>
      <div className="flex gap-2"><button disabled={disabled} className={button} onClick={() => void mutate(`references/${r.id}/`, "POST")}>다시 읽기</button><button disabled={disabled} className={button} onClick={() => void mutate(`references/${r.id}/`, "DELETE")}>자료 제외·삭제</button></div>
    </article>)}
  </div>;
}
