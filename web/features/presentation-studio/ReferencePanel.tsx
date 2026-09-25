"use client";
import { useState } from "react";
import { type Capabilities, type Project } from "./api";
import { input, button } from "./controls";

import ReferenceForm, { type ReferenceKind } from "./ReferenceForm";

type Props = { project: Project; capabilities?: Capabilities; disabled: boolean; mutate: (path: string, method: string, data?: object | FormData) => Promise<boolean> };
export default function ReferencePanel({ project, capabilities, disabled, mutate }: Props) {
  const [kind, setKind] = useState<ReferenceKind>("text");
  return <div className="space-y-5">
    <div><h2 className="font-bold">참고자료</h2><p className="mt-2 text-sm leading-6 text-slate-500">작성 지침, 프로젝트 코드, 웹 문서와 샘플 이미지를 모으세요. 웹·PC 경로는 AI 요청 때 다시 읽고, 요청에 관련된 발췌를 사용합니다.</p></div>
    <details className="rounded-xl bg-violet-50 p-4">
      <summary className="cursor-pointer text-sm font-semibold">텍스트·PC 경로로 추가</summary>
      <div className="mt-3 space-y-3">
        <label className="block text-sm">추가 방법<select className={input} value={kind} onChange={e => setKind(e.target.value as ReferenceKind)}><option value="text">직접 입력 / 붙여넣기</option>{capabilities?.local_paths_allowed && <option value="path">서버 PC 파일 / 프로젝트 폴더 경로</option>}</select></label>
        <ReferenceForm key={kind} kind={kind} capabilities={capabilities} disabled={disabled} mutate={mutate} />
      </div>
    </details>
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
