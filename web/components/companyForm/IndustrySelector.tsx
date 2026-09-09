"use client";

import { useEffect, useRef, useState } from "react";

export const INDUSTRY_OPTIONS = [
  "IT·소프트웨어",
  "정보통신",
  "교육",
  "연구·컨설팅",
  "광고·행사",
  "제조·물품",
  "건설·시설",
  "환경·안전",
  "의료·복지",
];

type IndustrySelectorProps = {
  initialIndustry?: string;
  initialRelatedIndustries?: string;
};

function parseIndustries(...values: string[]) {
  return listUnique(
    values.flatMap((value) =>
      value.split(",").map((item) => item.trim()).filter(Boolean),
    ),
  );
}

function listUnique(values: string[]) {
  return [...new Set(values)];
}

export default function IndustrySelector({
  initialIndustry = "",
  initialRelatedIndustries = "",
}: IndustrySelectorProps) {
  const initialValues = parseIndustries(initialIndustry, initialRelatedIndustries);
  const [industries, setIndustries] = useState(() =>
    initialValues.filter((item) => INDUSTRY_OPTIONS.includes(item)).slice(0, 5),
  ); // 목록에서 선택한 사업 분야
  const [customIndustries, setCustomIndustries] = useState(() =>
    initialValues.filter((item) => !INDUSTRY_OPTIONS.includes(item)).slice(0, 5),
  ); // 직접 입력해 추가한 사업 분야
  const [customInput, setCustomInput] = useState(""); // 아직 추가하지 않은 입력값
  const [isOpen, setIsOpen] = useState(false);
  const selectorRef = useRef<HTMLDivElement>(null);

  const savedIndustries = listUnique([
    ...industries,
    ...customIndustries,
  ]).slice(0, 5);

  useEffect(() => {
    function closeOutside(event: MouseEvent) {
      if (!selectorRef.current?.contains(event.target as Node)) setIsOpen(false);
    }

    document.addEventListener("mousedown", closeOutside);
    return () => document.removeEventListener("mousedown", closeOutside);
  }, []);

  function toggleIndustry(industry: string) {
    setIndustries((current) => {
      if (current.includes(industry)) {
        return current.filter((item) => item !== industry);
      }
      return savedIndustries.length < 5 ? [...current, industry] : current;
    });
  }

  function addCustomIndustry() {
    const newIndustry = customInput.trim();

    if (!newIndustry || savedIndustries.includes(newIndustry) || savedIndustries.length >= 5) {
      return;
    }

    setCustomIndustries((current) => [...current, newIndustry]);
    setCustomInput("");
  }

  return (
    <div className="md:col-span-2" ref={selectorRef}>
      <div className="flex items-center justify-between gap-3">
        <span className="text-sm font-semibold text-slate-800"><span className="text-red-500">* </span>사업 분야</span>
        <span className="text-xs text-slate-500">{savedIndustries.length} / 5개</span>
      </div>

      <div className="mt-2 grid gap-2 md:grid-cols-[220px_minmax(0,1fr)]">
        <div className="relative">
          <button
            aria-expanded={isOpen}
            className="flex h-11 w-full cursor-pointer items-center justify-between rounded-md border border-slate-300 bg-white px-3.5 text-sm text-slate-700 transition hover:border-blue-400"
            onClick={() => setIsOpen((current) => !current)}
            type="button"
          >
            사업 분야 선택
            <span aria-hidden="true" className="text-xs text-slate-400">▼</span>
          </button>

          {isOpen && (
            <div className="absolute left-0 top-full z-30 mt-1 w-full overflow-hidden rounded-md border border-slate-200 bg-white p-1.5 shadow-lg">
              {INDUSTRY_OPTIONS.map((industry) => {
                const isSelected = industries.includes(industry);
                const isDisabled = !isSelected && savedIndustries.length >= 5;

                return (
                  <button
                    className={`flex w-full items-center justify-between rounded px-3 py-2 text-left text-sm transition ${
                      isSelected ? "bg-blue-50 font-semibold text-blue-700" : "text-slate-700 hover:bg-blue-50"
                    } disabled:cursor-not-allowed disabled:opacity-40`}
                    disabled={isDisabled}
                    key={industry}
                    onClick={() => toggleIndustry(industry)}
                    type="button"
                  >
                    {industry}
                    {isSelected && <span aria-hidden="true">✓</span>}
                  </button>
                );
              })}
              <div className="mt-1 border-t border-slate-100 p-2">
                <div className="flex gap-2">
                  <input
                    className="h-9 min-w-0 flex-1 rounded-md border border-slate-300 px-3 text-sm outline-none placeholder:text-slate-400 focus:border-blue-500"
                    disabled={savedIndustries.length >= 5}
                    onChange={(event) => setCustomInput(event.target.value)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter") {
                        event.preventDefault();
                        addCustomIndustry();
                      }
                    }}
                    placeholder="직접 입력"
                    value={customInput}
                  />
                  <button
                    className="h-9 cursor-pointer rounded-md bg-blue-600 px-3 text-sm font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-slate-300"
                    disabled={!customInput.trim() || savedIndustries.length >= 5}
                    onClick={addCustomIndustry}
                    type="button"
                  >
                    추가
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="flex min-h-11 flex-wrap items-center gap-1.5 rounded-md border border-slate-300 bg-white px-2 py-1.5">
          {savedIndustries.length === 0 && <span className="px-1 text-sm text-slate-400">선택한 사업 분야가 표시됩니다.</span>}
          {savedIndustries.map((industry) => (
            <button
              aria-label={`${industry} 삭제`}
              className="rounded-md bg-blue-50 px-2.5 py-1.5 text-xs font-semibold text-blue-700 hover:bg-blue-100"
              key={industry}
              onClick={() => {
                if (customIndustries.includes(industry)) {
                  setCustomIndustries((current) => current.filter((item) => item !== industry));
                } else {
                  toggleIndustry(industry);
                }
              }}
              type="button"
            >
              {industry} ×
            </button>
          ))}
        </div>
      </div>
      <p className="mt-2 text-xs leading-5 text-slate-500">회사가 실제로 수행할 수 있는 분야를 최대 5개까지 선택하세요.</p>

      <input name="industry" readOnly type="hidden" value={savedIndustries.join(", ")} />
      <input name="related_industries" readOnly type="hidden" value="" />
    </div>
  );
}
