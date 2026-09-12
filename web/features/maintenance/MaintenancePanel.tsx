"use client";
import {useEffect,useState} from "react";
import Link from "next/link";
import {API_BASE_URL} from "@/lib/api";
type Route={provider:"ollama"|"openai";model:string};
type Config={mode:"local"|"hybrid";routes:Record<string,Route>};
type Data={config:Config;roles:Record<string,string>;saved:boolean;note:string};
export default function MaintenancePanel(){
 const [data,setData]=useState<Data>();const [draft,setDraft]=useState<Config>();
 const [status,setStatus]=useState<{ollama_reachable:boolean;models:string[];openai:string}>();
 const [error,setError]=useState("");const [message,setMessage]=useState("");const [busy,setBusy]=useState(false);
 const headers=()=>({Authorization:"Token "+localStorage.getItem("auth_token"),"Content-Type":"application/json"});
 useEffect(()=>{let live=true; const token=localStorage.getItem("auth_token");
 if(!token){const timer=window.setTimeout(()=>setError("관리자 계정으로 로그인해 주세요."),0);return()=>window.clearTimeout(timer);}
 fetch(API_BASE_URL+"/api/maintenance/routing/",{headers:{Authorization:"Token "+token}})
 .then(async r=>{if(!r.ok)throw Error(r.status===403?"관리자만 접근할 수 있습니다.":"설정을 불러올 수 없습니다.");return r.json();})
 .then(d=>{if(live){setData(d);setDraft(d.config);}})
 .catch(e=>{if(live)setError(e.message);});return()=>{live=false;};},[]);
 async function check(){setBusy(true);setError("");try{
 const r=await fetch(API_BASE_URL+"/api/maintenance/status/",{headers:headers()});if(!r.ok)throw Error("연결 확인에 실패했습니다.");setStatus(await r.json());
 }catch(e){setError(e instanceof Error?e.message:"오류");}finally{setBusy(false);}}
 async function save(){if(!draft)return;setBusy(true);setError("");setMessage("");try{
 const r=await fetch(API_BASE_URL+"/api/maintenance/routing/",{method:"PUT",headers:headers(),body:JSON.stringify(draft)});
 const d=await r.json();if(!r.ok)throw Error(d.error||"저장 실패");setData(d);setDraft(d.config);setMessage("저장했습니다. 새 AI 요청부터 적용됩니다.");
 }catch(e){setError(e instanceof Error?e.message:"오류");}finally{setBusy(false);}}
 function edit(role:string,value:Route){setDraft(d=>d?{...d,routes:{...d.routes,[role]:value}}:d);setMessage("");}
 return <main className="mx-auto w-full max-w-6xl px-5 py-10 text-slate-900">
 <Link href="/dashBoard" className="text-sm text-blue-700">← 업무 화면</Link>
 <h1 className="mt-4 text-2xl font-bold">AI 유지보수</h1>
 <p className="mt-2 text-sm text-slate-500">관리자 전용 · 이 노트북의 모든 사용자에게 적용되는 작업별 모델 설정</p>
 {error&&<p role="alert" className="mt-5 rounded bg-red-50 p-4 text-red-700">{error}</p>}
 {data&&draft&&<>
 <div className="mt-6 grid gap-4 md:grid-cols-3">{["OpenAI","Qwen · Ollama","Gemma · Ollama"].map((name,i)=><section key={name} className="rounded-xl border border-slate-200 border-t-4 border-t-emerald-500 bg-white p-5">
 <h2 className="font-bold">{name}</h2><p className="mt-3 text-sm text-slate-600">{i===0?(status?.openai||"잔액·실행 미확인"):(status?(status.ollama_reachable?"Ollama 연결됨":"Ollama 연결 실패"):"연결 미확인")}</p>
 <p className="mt-2 break-words text-xs text-slate-500">{i===0?"키는 서버에서 관리하며 화면에 노출하지 않습니다.":status?.models.filter(m=>m.toLowerCase().includes(i===1?"qwen":"gemma")).join(" · ")||"연결 확인 후 설치 목록 표시"}</p></section>)}</div>
 <button disabled={busy} onClick={check} className="mt-3 rounded border px-4 py-2 text-sm">연결·설치 모델 확인 (추론 없음)</button>
 <section className="mt-7 rounded-xl border bg-white p-5">
 <div className="flex flex-wrap items-center justify-between gap-4"><div><h2 className="text-lg font-bold">작업별 모델</h2><p className="mt-1 text-sm text-slate-500">자동 폴백 없음 · 저장한 설정과 편집 중인 설정을 비교하세요.</p></div>
 <label className="text-sm">실행 모드 <select disabled={busy} value={draft.mode} onChange={e=>{const mode=e.target.value as Config["mode"];setDraft({...draft,mode,routes:Object.fromEntries(Object.entries(draft.routes).map(([k,r])=>[k,mode==="local"&&r.provider==="openai"?{provider:"ollama",model:k==="VISION"?"gemma4:26b":"qwen3:14b"}:r]))});setMessage("");}} className="ml-2 rounded border p-2">
 <option value="local">로컬 전용 · OpenAI 차단</option><option value="hybrid">작업별 선택 · OpenAI 허용</option></select></label></div>
 {draft.mode==="hybrid"&&<p className="mt-4 text-sm text-amber-800">OpenAI로 지정한 작업은 자료를 외부 API로 전송하고 별도 API 비용이 발생합니다. 잔액이 없으면 해당 작업이 실패합니다.</p>}
 {!data.saved&&<p className="mt-4 text-sm text-slate-600">아직 관리자 설정을 저장하지 않았습니다. 아래는 로컬 전용 권장값입니다.</p>}
 <div className="mt-5 overflow-x-auto"><table className="w-full min-w-[680px] text-left text-sm"><thead className="bg-slate-50"><tr>{["작업","실행 제공자","모델 태그","저장된 경로"].map(x=><th key={x} className="p-3">{x}</th>)}</tr></thead>
 <tbody>{Object.entries(data.roles).map(([role,label])=>{const r=draft.routes[role];return <tr key={role} className="border-t"><td className="p-3 font-medium">{label}</td><td className="p-3"><select aria-label={label+" 제공자"} disabled={busy} value={r.provider==="openai"?"openai":r.model.toLowerCase().startsWith("gemma")?"gemma":r.model.toLowerCase().startsWith("qwen")?"qwen":"ollama"} onChange={e=>edit(role,{provider:e.target.value==="openai"?"openai":"ollama",model:e.target.value==="openai"?"gpt-4o-mini":e.target.value==="gemma"?"gemma4:26b":"qwen3:14b"})} className="rounded border p-2"><option value="qwen">Qwen · Ollama</option><option value="gemma">Gemma · Ollama</option><option value="ollama">기타 Ollama</option><option value="openai" disabled={draft.mode==="local"}>OpenAI</option></select></td>
 <td className="p-3"><input aria-label={label+" 모델"} disabled={busy} list={r.provider==="ollama"?"local-models":undefined} value={r.model} onChange={e=>edit(role,{...r,model:e.target.value})} className="w-full rounded border p-2"/>{role==="VISION"&&<p className="mt-1 text-xs text-slate-500">이미지 입력을 지원하는 모델 필요</p>}</td>
 <td className="p-3 text-xs text-slate-500">{data.saved?data.config.routes[role].provider+" / "+data.config.routes[role].model:"서버 기본 설정"}</td></tr>;})}</tbody></table></div>
 <datalist id="local-models">{(status?.models||["qwen3:14b","gemma4:26b"]).map(m=><option key={m} value={m}/>)}</datalist>
 <p className="mt-4 text-xs leading-6 text-slate-500">{data.note}<br/>사업자등록증 텍스트 설정은 로컬 이미지 경로의 텍스트 PDF 추출에 적용됩니다. OpenAI 이미지 경로는 PDF도 함께 처리합니다. 모델 설치·키 변경은 이 화면에서 수행하지 않습니다.</p>
 <div className="mt-5 flex gap-3"><button disabled={busy} onClick={save} className="rounded bg-blue-600 px-5 py-2 font-semibold text-white disabled:opacity-50">{busy?"처리 중…":"설정 저장"}</button><button disabled={busy} onClick={()=>{setDraft(data.config);setMessage("");}} className="rounded border px-4 py-2">편집 취소</button></div>
 {message&&<p role="status" className="mt-3 text-sm text-emerald-700">{message}</p>}
 </section></>}
 </main>;
}
