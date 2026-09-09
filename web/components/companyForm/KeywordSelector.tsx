"use client";

import { KeyboardEvent, useState } from "react";

type KeywordSelectorProps = {
  keywords: string[];
  onChange: (keywords: string[]) => void;
  name: string;
  label?: string;
  description?: string;
  required?: boolean;
  tone?: "blue" | "red";
};

const toneClasses = {
  blue: {
    container: "focus-within:border-blue-500 focus-within:ring-blue-100",
    tag: "bg-blue-50 text-blue-700",
    remove: "text-blue-500 hover:text-blue-800",
  },
  red: {
    container: "focus-within:border-red-400 focus-within:ring-red-100",
    tag: "bg-red-50 text-red-700",
    remove: "text-red-400 hover:text-red-700",
  },
};

export default function KeywordSelector({
  keywords,
  onChange,
  name,
  label = "희망 키워드",
  description = "찾고 싶은 공고의 핵심 업무를 하나씩 추가해 주세요.",
  required = true,
  tone = "blue",
}: KeywordSelectorProps) {
  const [inputValue, setInputValue] = useState("");
  const colors = toneClasses[tone];

  function addKeyword() {
    const keyword = inputValue.trim().replace(/,$/, "");
    if (keyword && !keywords.includes(keyword)) onChange([...keywords, keyword]);
    setInputValue("");
  }

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Enter" || event.key === ",") {
      event.preventDefault();
      addKeyword();
    }
  }

  return (
    <div>
      <span className="text-sm font-semibold text-slate-800">
        {required && <span className="text-red-500">* </span>}
        {label}
      </span>
      <div className={`mt-2 flex min-h-11 flex-wrap items-center gap-2 rounded-md border border-slate-300 bg-white px-2.5 py-1.5 focus-within:ring-2 ${colors.container}`}>
        {keywords.map((keyword) => (
          <span
            className={`inline-flex items-center gap-1 rounded-md px-2.5 py-1.5 text-sm font-semibold ${colors.tag}`}
            key={keyword}
          >
            {keyword}
            <button
              aria-label={`${keyword} 삭제`}
              className={`h-5 w-5 cursor-pointer text-base leading-none ${colors.remove}`}
              onClick={() => onChange(keywords.filter((item) => item !== keyword))}
              title="삭제"
              type="button"
            >
              ×
            </button>
          </span>
        ))}
        <input
          className="h-8 min-w-40 flex-1 border-0 px-1 text-sm outline-none placeholder:text-slate-400"
          onBlur={addKeyword}
          onChange={(event) => setInputValue(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="키워드를 입력하고 Enter를 누르세요."
          value={inputValue}
        />
      </div>
      <input name={name} readOnly type="hidden" value={keywords.join(", ")} />
      <p className="mt-2 text-xs text-slate-500">{description}</p>
    </div>
  );
}
