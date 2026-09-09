import ProcessCarousel from "@/components/home/ProcessCarousel"; // 서비스 4단계를 순환해서 보여주는 컴포넌트
import Header from "@/components/layout/Header"; // 상단 메뉴 컴포넌트

export default function MainPage() { // /mainPage 주소에서 보이는 메인 페이지
  return (
    <main className="min-h-screen bg-transparent text-slate-950"> {/* 페이지 전체 영역 */}
      <Header /> {/* 상단 메뉴 */}

      <section className="mx-auto flex max-w-5xl flex-col items-center px-6 pb-12 pt-20 text-center"> {/* 메인 소개 영역 */}
        <h1 className="max-w-2xl text-4xl font-bold leading-tight">AI 원스톱 입찰 서비스</h1>
        <div className="mt-5 flex items-center justify-center gap-3">
          <span aria-hidden="true" className="h-px w-8 bg-slate-300" />
          <p className="text-base leading-7 text-slate-600">
            입찰 공고 추천부터 제안서 작성까지 <strong className="font-semibold text-blue-600">5분 안에</strong> 끝납니다
          </p>
          <span aria-hidden="true" className="h-px w-8 bg-slate-300" />
        </div>
      </section>

      <ProcessCarousel /> {/* 1~4단계가 3초마다 입체적으로 순환하는 영역 */}
    </main>
  );
}
