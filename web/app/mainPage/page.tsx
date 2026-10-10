import Link from "next/link";
import Header from "@/components/layout/Header";

const steps = [
  ["01", "자료를 모으고", "공고와 회사 근거, 참고할 문서를 준비합니다."],
  ["02", "구조를 설계하고", "요구사항과 평가항목에 맞춰 작성 계획을 세웁니다."],
  ["03", "함께 다듬고", "미리보기를 보며 AI와 페이지별로 수정합니다."],
  ["04", "확인한 뒤 내보내기", "본문과 근거를 대조하고 편집 가능한 PPTX로 받습니다."],
];
const questions = [
  ['OpenAI API 잔액이 없어도 사용할 수 있나요?','로컬 AI 모드에서는 노트북의 Gemma로 작성하며 OpenAI 키나 잔액이 필요하지 않습니다. 서버 PC와 로컬 모델이 켜져 있어야 합니다. 관리자 설정에서 일부 입찰 작업의 모델을 바꿀 수도 있습니다.'],
  ['만들던 PPTX를 이어서 작성할 수 있나요?','발표자료 작업실에서 PPTX와 참고자료를 올려 이어서 작업할 수 있습니다. 유지할 페이지를 설정하고 AI에 수정할 부분을 요청하세요.'],
  ['업로드하면 노트북의 원본 파일이 바뀌나요?','업로드한 복사본으로 작업합니다. 노트북의 원본은 바뀌지 않으며, 작업한 파일은 다시 다운로드할 수 있습니다.'],
  ['AI가 만든 제안서를 바로 제출해도 되나요?','초안을 검토하고 공고의 최신 변경, 참가 자격, 실제 회사 증빙, 지정 서식과 가격을 확인해야 합니다. AI 검수는 담당자의 최종 검토를 돕습니다.'],
];

export default function MainPage() {
  return (
    <main className="min-h-screen bg-[#f6f5f1] text-[#172c3a]">
      <Header home />
      <section className="mx-auto grid max-w-6xl items-center gap-12 px-5 pb-16 pt-14 sm:px-8 sm:pt-20 lg:grid-cols-[1fr_1.05fr] lg:gap-10 lg:pb-24 lg:pt-24">
        <div>
          <p className="flex items-center gap-3 text-xs font-semibold tracking-[0.14em] text-slate-600"><span className="h-2 w-2 rounded-full bg-teal-600" />AI BID · DOCUMENT WORKSPACE</p>
          <h1 className="mt-7 text-[2.65rem] font-bold leading-[1.24] tracking-[-0.045em] [word-break:keep-all] sm:text-6xl lg:text-[3.65rem]">좋은 제안은,<br /><span className="text-blue-700">근거에서</span> 시작됩니다.</h1>
          <p className="mt-6 max-w-md text-base leading-8 text-slate-600 [word-break:keep-all]">공고를 읽는 일부터 제안서를 다듬는 일까지.<br className="hidden sm:block" />흩어진 자료를 모아, 설득력 있는 문서로 연결하세요.</p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link href="/dashBoard/bidList" className="inline-flex min-h-12 items-center gap-6 rounded-lg bg-[#172c3a] px-6 py-3 text-sm font-semibold text-white hover:bg-blue-800">입찰 공고 찾아보기 <span aria-hidden="true">↗</span></Link>
            <Link href="/dashBoard/presentations" className="inline-flex min-h-12 items-center gap-4 rounded-lg border border-slate-300 bg-white/60 px-5 py-3 text-sm font-semibold hover:bg-white">발표자료 작성하기 <span aria-hidden="true">→</span></Link>
          </div>
          <p className="mt-5 text-xs leading-6 text-slate-500">회사 자료와 공고 원문을 참고하고, 확인이 필요한 내용은 따로 검토합니다.</p>
        </div>
        <div className="relative min-w-0 rounded-2xl bg-[#e4e9e5] p-4 sm:p-7" aria-label="제안서 작업 흐름 예시">
          <div className="mb-5 flex items-center justify-between text-[11px] font-medium text-slate-600"><span>FROM SOURCE TO PROPOSAL</span><span className="rounded-full border border-slate-400/40 px-2.5 py-1">작업 흐름 예시</span></div>
          <div className="overflow-hidden rounded-xl border border-white/80 bg-white shadow-[0_18px_45px_-20px_rgba(23,44,58,0.35)]">
            <div className="flex items-center justify-between border-b border-slate-100 px-5 py-3 text-xs"><span className="font-semibold">AI비드 · 제안서 작업실</span><span className="text-slate-400">수행 계획</span></div>
            <div className="grid grid-cols-[38px_1fr] sm:grid-cols-[50px_1fr]">
              <div className="space-y-4 border-r border-slate-100 bg-slate-50 px-2 py-5 text-center text-[10px] text-slate-400"><span className="block">01</span><span className="block rounded bg-blue-100 py-1.5 font-bold text-blue-700">02</span><span className="block">03</span><span className="block">04</span></div>
              <div className="p-5 sm:p-7">
                <div className="flex items-center justify-between text-[9px] tracking-wider text-slate-400"><span>PROJECT PROPOSAL</span><span>02 / 04</span></div>
                <h2 className="mt-7 text-2xl font-bold leading-snug sm:text-3xl">목표를 실행으로 잇는<br />구체적인 수행 계획</h2>
                <div className="mb-6 mt-4 h-1 w-9 bg-teal-500" />
                <div className="grid grid-cols-3 gap-2 border-t border-slate-200 pt-4">
                  {[['요구사항','원문 분석'],['수행 방법','단계별 설계'],['결과 확인','산출물 검토']].map(([title,body],i)=><div key={title}><p className="text-[10px] text-teal-700">0{i+1}</p><p className="mt-2 text-xs font-semibold">{title}</p><p className="mt-1 text-[10px] text-slate-400">{body}</p></div>)}
                </div>
              </div>
            </div>
          </div>
          <div className="ml-6 mt-4 flex items-start gap-3 rounded-lg border border-white/80 bg-[#f7faf7] p-4 shadow-sm sm:ml-12"><span aria-hidden="true" className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-teal-100 text-sm text-teal-800">✓</span><div><p className="text-xs font-semibold">작성된 문장에 근거를 연결합니다</p><p className="mt-1 text-[11px] leading-5 text-slate-500">요구사항 · 원문 출처 · 답변 페이지를 함께 대조</p></div></div>
          <p className="mt-4 text-[10px] leading-5 text-slate-500">기능을 설명하기 위한 예시입니다. 실제 생성 문서나 검수 결과가 아닙니다.</p>
        </div>
      </section>
      <section id="workspaces" className="scroll-mt-24 border-y border-slate-200 bg-white">
        <div className="mx-auto max-w-6xl px-5 py-14 sm:px-8 sm:py-20">
          <div className="mb-9 flex flex-wrap items-end justify-between gap-4"><div><p className="text-xs font-semibold tracking-widest text-teal-700">CHOOSE YOUR WORKSPACE</p><h2 className="mt-3 text-2xl font-bold tracking-tight sm:text-3xl">지금, 어떤 문서를 만들까요?</h2></div><Link href="/dashBoard/templates" className="text-sm text-slate-600 underline decoration-slate-300 underline-offset-4 hover:text-blue-700">PPT 양식 둘러보기 ↗</Link></div>
          <div className="grid gap-6 md:grid-cols-2">
            <article className="flex flex-col rounded-xl border border-slate-200 bg-[#f7f9fb] p-7 sm:p-9"><p className="text-xs font-semibold text-blue-700">BID WORKSPACE</p><h3 className="mt-4 text-2xl font-bold">입찰 제안서</h3><p className="mt-4 max-w-sm text-sm leading-7 text-slate-600">우리 회사에 맞는 공고를 찾고, 평가항목과 회사 근거에 맞춰 제안서를 작성합니다.</p><ul className="mb-8 mt-6 space-y-3 text-sm text-slate-600">{['공고 검색과 회사 조건에 맞는 추천','평가항목별 작성 계획과 출처 대조','최종 문서 전체 AI 검수'].map(text=><li key={text} className="flex gap-3"><span aria-hidden="true" className="text-blue-600">↳</span>{text}</li>)}</ul><Link href="/dashBoard/matchBid" className="mt-auto flex items-center justify-between border-t border-slate-200 pt-5 text-sm font-semibold text-blue-700">제안서 작업실 열기 <span aria-hidden="true">→</span></Link></article>
            <article className="flex flex-col rounded-xl border border-[#e6e0ed] bg-[#f8f6fa] p-7 sm:p-9"><p className="text-xs font-semibold text-violet-700">PRESENTATION STUDIO</p><h3 className="mt-4 text-2xl font-bold">발표자료</h3><p className="mt-4 max-w-sm text-sm leading-7 text-slate-600">수업 발표부터 프로젝트 소개까지. 원하는 양식과 참고자료로 만들고 한 장씩 다듬습니다.</p><ul className="mb-8 mt-6 space-y-3 text-sm text-slate-600">{['만들던 PPTX 업로드와 페이지 보존','참고 URL · 문서 · 이미지 활용','AI와 대화하며 페이지별 수정'].map(text=><li key={text} className="flex gap-3"><span aria-hidden="true" className="text-violet-600">↳</span>{text}</li>)}</ul><Link href="/dashBoard/presentations" className="mt-auto flex items-center justify-between border-t border-[#e6e0ed] pt-5 text-sm font-semibold text-violet-700">발표자료 작업실 열기 <span aria-hidden="true">→</span></Link></article>
          </div>
        </div>
      </section>
      <section id="how-it-works" className="mx-auto max-w-6xl scroll-mt-24 px-5 py-16 sm:px-8 sm:py-20">
        <p className="text-xs font-semibold tracking-widest text-teal-700">A CLEARER WAY TO WORK</p><h2 className="mt-3 text-2xl font-bold tracking-tight sm:text-3xl">빈 문서부터 시작하지 않아도 됩니다.</h2>
        <div className="mt-10 grid gap-8 sm:grid-cols-2 lg:grid-cols-4">{steps.map(([number,title,description])=><article key={number} className="border-t border-slate-300 pt-5"><p className="font-mono text-sm text-teal-700">{number}</p><h3 className="mt-5 text-lg font-semibold">{title}</h3><p className="mt-3 text-sm leading-7 text-slate-600">{description}</p></article>)}</div>
      </section>
      <section id="questions" className="border-t border-slate-200 bg-white">
        <div className="mx-auto grid max-w-6xl gap-8 px-5 py-14 sm:px-8 sm:py-20 md:grid-cols-[1fr_1.5fr]"><div><p className="text-xs font-semibold tracking-widest text-teal-700">BEFORE YOU START</p><h2 className="mt-3 text-2xl font-bold">궁금한 점을 먼저 확인하세요.</h2></div><div className="divide-y divide-slate-200 border-y border-slate-200">{questions.map(([question,answer])=><details key={question} className="group py-5"><summary className="flex cursor-pointer list-none items-center justify-between gap-5 text-sm font-semibold [&::-webkit-details-marker]:hidden">{question}<span aria-hidden="true" className="text-lg font-normal text-slate-400 group-open:rotate-45">+</span></summary><p className="mt-4 pr-6 text-sm leading-7 text-slate-600">{answer}</p></details>)}</div></div>
      </section>
      <footer className="bg-[#172c3a] text-white"><div className="mx-auto flex max-w-6xl flex-col justify-between gap-7 px-5 py-10 sm:flex-row sm:items-center sm:px-8"><div><p className="text-lg font-bold">AI비드</p><p className="mt-2 text-xs leading-6 text-slate-300">자료에서 문서까지, 근거 있는 업무의 시작.</p></div><nav aria-label="바로가기" className="flex flex-wrap gap-6 text-sm text-slate-200"><Link href="/dashBoard/myCompanyInfo" className="hover:text-white">회사정보</Link><Link href="/dashBoard/matchBid" className="hover:text-white">제안서 작업실</Link><Link href="/dashBoard/presentations" className="hover:text-white">발표자료 작업실</Link></nav></div></footer>
    </main>
  );
}
