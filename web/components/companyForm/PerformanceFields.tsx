"use client";

import { useState } from "react";

import { formatWonInput, normalizeWonInput } from "@/components/ui/WonInput";

type Performance = {
  client: string;
  year: string;
  amount: string;
  description: string;
};

function parsePerformances(value = "") {
  const items = value
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const [client = "", year = "", amount = "", ...description] = line
        .split("|")
        .map((item) => item.trim());

      return { client, year, amount, description: description.join(" | ") };
    });

  return items.length
    ? items
    : [{ client: "", year: "", amount: "", description: "" }];
}

export default function PerformanceFields({ initialValue = "" }: { initialValue?: string }) {
  const [items, setItems] = useState<Performance[]>(() => parsePerformances(initialValue));
  const currentYear = new Date().getFullYear();
  const years = Array.from({ length: currentYear - 1990 + 1 }, (_, index) => currentYear - index);

  function updateItem(index: number, field: keyof Performance, value: string) {
    setItems(items.map((item, itemIndex) =>
      itemIndex === index ? { ...item, [field]: value } : item,
    ));
  }

  function removeItem(index: number) {
    setItems(items.filter((_, itemIndex) => itemIndex !== index));
  }

  const serializedValue = items
    .filter((item) => item.client || item.year || item.amount || item.description)
    .map((item) => `${item.client} | ${item.year} | ${item.amount} | ${item.description}`)
    .join("\n");

  return (
    <div className="md:col-span-2">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-slate-800">과거 수행 실적</h3>
          <p className="mt-1 text-xs text-slate-500">입찰과 관련 있는 대표 실적부터 입력해 주세요.</p>
        </div>
        <button
          className="cursor-pointer rounded-md border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-700 hover:border-blue-400 hover:text-blue-600"
          onClick={() => setItems([...items, { client: "", year: "", amount: "", description: "" }])}
          type="button"
        >
          + 실적 추가
        </button>
      </div>

      <div className="mt-3 max-w-[52rem] space-y-3">
        {items.map((item, index) => (
          <div className="rounded-lg border border-slate-200 bg-slate-50/60 p-4" key={index}>
            <div className="mb-3 flex items-center justify-between gap-3">
              <p className="text-xs font-semibold text-slate-500">수행 실적 {index + 1}</p>
              {index > 0 && (
                <button
                  className="cursor-pointer rounded-md border border-red-200 bg-white px-3 py-1.5 text-xs font-semibold text-red-600 hover:bg-red-50"
                  onClick={() => removeItem(index)}
                  type="button"
                >
                  실적 삭제
                </button>
              )}
            </div>

            <div className="grid gap-3 sm:grid-cols-[minmax(220px,1fr)_140px_160px]">
              <label className="block">
                <span className="text-xs font-semibold text-slate-600">발주처</span>
                <input
                  className="mt-1.5 h-10 w-full rounded-md border border-slate-300 bg-white px-3 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                  onChange={(event) => updateItem(index, "client", event.target.value)}
                  placeholder="예: 서울시청"
                  value={item.client}
                />
              </label>

              <label className="block">
                <span className="text-xs font-semibold text-slate-600">수행연도</span>
                <select
                  className="mt-1.5 h-10 w-full cursor-pointer rounded-md border border-slate-300 bg-white px-3 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                  onChange={(event) => updateItem(index, "year", event.target.value)}
                  value={item.year}
                >
                  <option value="">연도 선택</option>
                  {years.map((year) => <option key={year} value={year}>{year}</option>)}
                </select>
              </label>

              <label className="block">
                <span className="text-xs font-semibold text-slate-600">사업비 (원)</span>
                <input
                  className="mt-1.5 h-10 w-full rounded-md border border-slate-300 bg-white px-3 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                  inputMode="numeric"
                  onChange={(event) => updateItem(index, "amount", normalizeWonInput(event.target.value))}
                  placeholder="예: 100,000,000"
                  value={formatWonInput(item.amount)}
                />
              </label>

            </div>

            <label className="mt-3 block">
              <span className="text-xs font-semibold text-slate-600">사업내용</span>
              <input
                className="mt-1.5 h-10 w-full rounded-md border border-slate-300 bg-white px-3 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                onChange={(event) => updateItem(index, "description", event.target.value)}
                placeholder="예: 공공기관 홈페이지 구축, 운영 및 유지보수"
                type="text"
                value={item.description}
              />
            </label>
          </div>
        ))}
      </div>

      <input name="past_performance" readOnly type="hidden" value={serializedValue} />
    </div>
  );
}
