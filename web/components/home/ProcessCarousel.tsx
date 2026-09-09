"use client"; // 시간에 따라 카드를 바꾸므로 브라우저에서 실행되는 React 컴포넌트

import { useEffect, useState, type CSSProperties } from "react";

const STEPS = [
  {
    title: "1. 회사 정보 입력",
    description: "회사 기본 정보와 보유 역량, 희망 입찰 조건을 상세히 입력합니다.",
    examples: [],
  },
  {
    title: "2. 공고 추천받기",
    description: "AI가 매칭되는 공고를 실시간으로 찾아 문자나 이메일로 알림을 보내드립니다.",
    examples: [],
  },
  {
    title: "3. AI봇에게 물어보기",
    description: "공고문과 회사 정보를 바탕으로 궁금한 내용을 바로 확인합니다.",
    examples: [
      "이 입찰, 우리가 성공할 확률은?",
      "이 입찰에서 이기려면 어떤 전략이 좋을지 추천해 줘.",
      "제안요청서에서 가장 핵심적으로 요구하는 내용을 5줄로 요약해 줘.",
    ],
  },
  {
    title: "4. 제안서 제작하기",
    description: "AI가 5분 안에 제안서를 작성해 줍니다.",
    examples: [],
  },
];

function getCardStyle(
  index: number,
  activeIndex: number,
): CSSProperties {
  const offset = (index - activeIndex + STEPS.length) % STEPS.length;
  let style: CSSProperties;

  if (offset === 0) {
    style = {
      filter: "none",
      opacity: 1,
      transform: "none", // 앞쪽 카드는 변형하지 않아 글자를 선명하게 표시
      zIndex: 50,
    };
  } else if (offset === 1) {
    style = {
      filter: "saturate(0.65)",
      opacity: 0.48,
      transform: "translateX(42%) translateZ(-90px) rotateY(-14deg) scale(0.8)",
      zIndex: 30,
    };
  } else if (offset === STEPS.length - 1) {
    style = {
      filter: "saturate(0.65)",
      opacity: 0.48,
      transform: "translateX(-42%) translateZ(-90px) rotateY(14deg) scale(0.8)",
      zIndex: 30,
    };
  } else {
    style = {
      filter: "saturate(0.55)",
      opacity: 0.34,
      transform: "translateY(-64px) translateZ(-160px) rotateX(-8deg) scale(0.72)",
      zIndex: 20,
    };
  }

  return style;
}

export default function ProcessCarousel() {
  const [activeIndex, setActiveIndex] = useState(0); // 현재 화면 앞쪽에 보이는 카드 번호
  const [isPaused, setIsPaused] = useState(false); // 마우스를 올리면 자동 회전을 잠시 멈춤
  const [hasInteracted, setHasInteracted] = useState(false); // 사용자가 직접 넘기면 새로고침 전까지 자동 회전 중지

  useEffect(() => {
    if (isPaused || hasInteracted) return;

    const timer = window.setTimeout(() => {
      setActiveIndex((activeIndex + 1) % STEPS.length);
    }, 3000);

    return () => window.clearTimeout(timer); // 컴포넌트가 사라지면 타이머 정리
  }, [activeIndex, hasInteracted, isPaused]);

  function moveTo(nextIndex: number) {
    if (nextIndex === activeIndex) return;

    setActiveIndex(nextIndex);
  }

  function showPrevious() {
    setHasInteracted(true); // 사용자가 조작했으므로 자동 회전 중지
    moveTo((activeIndex - 1 + STEPS.length) % STEPS.length);
  }

  function showNext() {
    setHasInteracted(true); // 사용자가 조작했으므로 자동 회전 중지
    moveTo((activeIndex + 1) % STEPS.length);
  }

  function showStep(index: number) {
    setHasInteracted(true);
    moveTo(index);
  }

  return (
    <section
      aria-label="AI 입찰 서비스 이용 단계"
      className="mx-auto w-full max-w-5xl px-6 pb-20"
      onBlur={() => setIsPaused(false)}
      onFocus={() => setIsPaused(true)}
      onMouseEnter={() => setIsPaused(true)}
      onMouseLeave={() => setIsPaused(false)}
    >
      <div className="mx-auto grid max-w-5xl grid-cols-[42px_minmax(0,1fr)_42px] items-center gap-2 sm:grid-cols-[48px_minmax(0,1fr)_48px] sm:gap-4">
        <button
          aria-label="이전 단계"
          className="relative z-50 flex h-10 w-10 items-center justify-center justify-self-center rounded-full border border-slate-200 bg-white/80 text-3xl font-light leading-none text-slate-400 shadow-sm transition hover:border-slate-300 hover:bg-white hover:text-slate-600 sm:h-11 sm:w-11"
          onClick={showPrevious}
          title="이전 단계"
          type="button"
        >
          ‹
        </button>

        <div className="relative h-[350px] overflow-x-clip overflow-y-visible [perspective:1200px] [transform-style:preserve-3d]">
          {STEPS.map((step, index) => (
            <article
              aria-hidden={index !== activeIndex}
              className={`absolute inset-x-0 top-20 mx-auto h-[245px] w-[90%] overflow-hidden rounded-lg border px-7 py-7 text-left transition-[transform,opacity,filter,box-shadow,background-color,border-color] duration-700 ease-in-out sm:w-[58%] ${
                index === activeIndex
                  ? "border-slate-300 bg-white shadow-xl shadow-slate-300/40"
                  : "border-slate-200 bg-slate-50 shadow-sm"
              }`}
              key={step.title}
              style={{
                ...getCardStyle(index, activeIndex),
                transformOrigin: "center top",
              }}
            >
              <div className="flex items-center justify-between">
                <p className="text-xs font-semibold text-blue-600">AI 입찰 업무 {index + 1}단계</p>
                <p className="text-xs text-slate-400">0{index + 1} / 04</p>
              </div>

              <h2 className="mt-3 text-xl font-bold text-slate-950">{step.title}</h2>
              <p className="mt-4 text-sm leading-6 text-slate-600">{step.description}</p>

              {step.examples.length > 0 && (
                <ul className="mt-4 space-y-1.5 text-xs leading-5 text-slate-500">
                  {step.examples.map((example) => (
                    <li key={example}>“{example}”</li>
                  ))}
                </ul>
              )}
            </article>
          ))}
        </div>

        <button
          aria-label="다음 단계"
          className="relative z-50 flex h-10 w-10 items-center justify-center justify-self-center rounded-full border border-slate-200 bg-white/80 text-3xl font-light leading-none text-slate-400 shadow-sm transition hover:border-slate-300 hover:bg-white hover:text-slate-600 sm:h-11 sm:w-11"
          onClick={showNext}
          title="다음 단계"
          type="button"
        >
          ›
        </button>
      </div>

      <div className="mt-2 flex justify-center gap-2" aria-label="서비스 단계 선택">
        {STEPS.map((step, index) => (
          <button
            aria-label={`${index + 1}단계 보기`}
            className={`h-2.5 w-2.5 rounded-full transition-colors ${
              index === activeIndex ? "bg-blue-600" : "bg-slate-300 hover:bg-slate-400"
            }`}
            key={step.title}
            onClick={() => showStep(index)}
            type="button"
          />
        ))}
      </div>
    </section>
  );
}
