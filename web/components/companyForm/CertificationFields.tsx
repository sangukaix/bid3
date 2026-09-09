"use client";

import { useState } from "react";

type Certification = {
  name: string;
  issuer: string;
  year: string;
};

function parseCertifications(value = "") {
  const items = value
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const [name = "", issuer = "", year = ""] = line.split("|").map((item) => item.trim());
      return { name, issuer, year };
    });

  return items.length ? items : [{ name: "", issuer: "", year: "" }];
}

export default function CertificationFields({ initialValue = "" }: { initialValue?: string }) {
  const [items, setItems] = useState<Certification[]>(() => parseCertifications(initialValue));
  const currentYear = new Date().getFullYear();
  const years = Array.from({ length: currentYear - 1990 + 1 }, (_, index) => currentYear - index);

  function updateItem(index: number, field: keyof Certification, value: string) {
    setItems(items.map((item, itemIndex) =>
      itemIndex === index ? { ...item, [field]: value } : item,
    ));
  }

  function removeLastItem() {
    if (items.length > 1) setItems(items.slice(0, -1));
  }

  const serializedValue = items
    .filter((item) => item.name || item.issuer || item.year)
    .map((item) => `${item.name} | ${item.issuer} | ${item.year}`)
    .join("\n");

  return (
    <div className="md:col-span-2">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-slate-800">입찰 참가 자격 증빙</h3>
          <p className="mt-1 text-xs text-slate-500">
            회사가 보유한 업종 면허, 사업 등록 또는 품질·기술 인증을 입력해 주세요.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            className="cursor-pointer rounded-md border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-700 hover:border-blue-400 hover:text-blue-600"
            onClick={() => setItems([...items, { name: "", issuer: "", year: "" }])}
            type="button"
          >
            + 자격 증빙 추가
          </button>
          {items.length > 1 && (
            <button
              className="cursor-pointer rounded-md border border-red-200 bg-white px-3 py-2 text-xs font-semibold text-red-600 hover:bg-red-50"
              onClick={removeLastItem}
              type="button"
            >
              증빙 삭제
            </button>
          )}
        </div>
      </div>

      <div className="mt-3 max-w-[52rem] space-y-3">
        {items.map((item, index) => (
          <div className="rounded-lg border border-slate-200 bg-slate-50/60 p-4" key={index}>
            <div className="max-w-xl">
              <label className="block">
                <span className="text-xs font-semibold text-slate-600">자격·면허·인증명</span>
                <input
                  className="mt-1.5 h-10 w-full rounded-md border border-slate-300 bg-white px-3 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                  onChange={(event) => updateItem(index, "name", event.target.value)}
                  placeholder="예: 정보통신공사업 등록, ISO 9001, 직접생산확인증명서"
                  value={item.name}
                />
              </label>
            </div>

            <div className="mt-3 grid max-w-xl gap-3 sm:grid-cols-[minmax(0,1fr)_150px]">
              <label className="block">
                <span className="text-xs font-semibold text-slate-600">발급기관 (선택)</span>
                <input
                  className="mt-1.5 h-10 w-full rounded-md border border-slate-300 bg-white px-3 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                  onChange={(event) => updateItem(index, "issuer", event.target.value)}
                  placeholder="예: 한국품질인증원"
                  value={item.issuer}
                />
              </label>

              <label className="block">
                <span className="text-xs font-semibold text-slate-600">취득연도 (선택)</span>
                <select
                  className="mt-1.5 h-10 w-full cursor-pointer rounded-md border border-slate-300 bg-white px-3 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                  onChange={(event) => updateItem(index, "year", event.target.value)}
                  value={item.year}
                >
                  <option value="">연도 선택</option>
                  {years.map((year) => <option key={year} value={year}>{year}</option>)}
                </select>
              </label>
            </div>
          </div>
        ))}
      </div>

      <input name="licenses" readOnly type="hidden" value={serializedValue} />
    </div>
  );
}
