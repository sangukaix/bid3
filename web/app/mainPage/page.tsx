import Link from "next/link";
import Image from "next/image";
import Header from "@/components/layout/Header";
import ProductDemo from "@/features/product-demo/ProductDemo";
import storyboard from "@/features/product-demo/storyboard.json";
import demoPoster from "@/public/product-demo/poster.webp";

const demoDuration = storyboard.scenes.reduce((total, scene) => total + scene.duration, 0);

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
        <a href="#product-demo" aria-label="AI비드 서비스 소개 영상 보기" className="group relative block min-w-0 rounded-2xl border border-[#cbd8d0] bg-[#e4e9e5] p-4 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-teal-600 sm:p-5">
          <div className="mb-4 flex items-center justify-between text-[10px] font-semibold tracking-wider text-slate-600"><span>A LOOK INSIDE AI BID</span><span className="rounded-full border border-[#bacbc1] px-2.5 py-1">{demoDuration}초 서비스 시연</span></div>
          <div className="relative overflow-hidden rounded-xl bg-[#102630] shadow-[0_18px_45px_-20px_rgba(23,44,58,0.45)]">
            <Image src={demoPoster} alt="공고 검토부터 제안서 작성, Gemma와 발표자료 수정까지 보여주는 AI비드 소개" sizes="(min-width: 1024px) 550px, (min-width: 640px) 85vw, 90vw" priority className="h-auto w-full transition-transform duration-500 motion-safe:group-hover:scale-[1.025]" />
            <span aria-hidden="true" className="absolute bottom-4 right-4 flex h-12 w-12 items-center justify-center rounded-full border border-white/40 bg-white/90 text-[#102630] shadow-lg transition-colors group-hover:bg-[#8ee0c7]"><svg width="17" height="17" viewBox="0 0 20 20" fill="currentColor"><path d="M6 3.8a.8.8 0 0 1 1.2-.7l10 6.2a.8.8 0 0 1 0 1.4l-10 6.2a.8.8 0 0 1-1.2-.7Z" /></svg></span>
          </div>
          <div className="mt-5 flex items-start justify-between gap-4 px-1"><div><p className="text-sm font-bold">자료에서 문서까지, 실제 화면으로.</p><p className="mt-2 text-xs leading-6 text-slate-600">공고 찾기 · 제안서 검토 · 내 PPTX 이어 만들기</p></div><span aria-hidden="true" className="mt-1 text-lg text-teal-800">↗</span></div>
        </a>
      </section>
      <ProductDemo />
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
