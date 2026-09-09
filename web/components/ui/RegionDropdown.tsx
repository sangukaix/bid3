"use client";

import { useEffect, useRef, useState } from "react";

export const REGION_OPTIONS = [
  "서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종",
  "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주",
];

type RegionDropdownProps = {
  regions: string[];
  onSelect: (region: string) => void;
  variant?: "inline" | "field";
};

export default function RegionDropdown({
  regions,
  onSelect,
  variant = "inline",
}: RegionDropdownProps) {
  const dropdownRef = useRef<HTMLDivElement>(null);
  const [isOpen, setIsOpen] = useState(false);
  const summaryClassName = variant === "field"
    ? "flex h-11 w-full cursor-pointer list-none items-center justify-between rounded-md border border-slate-300 bg-white px-3.5 text-sm text-slate-700 outline-none transition hover:border-blue-400 [&::-webkit-details-marker]:hidden"
    : "flex h-8 min-w-24 cursor-pointer list-none items-center justify-between gap-3 px-1 text-sm text-slate-600 outline-none [&::-webkit-details-marker]:hidden";
  const menuClassName = variant === "field"
    ? "absolute right-0 top-full z-30 mt-1 max-h-64 min-w-40 overflow-y-auto rounded-md border border-slate-200 bg-white p-1.5 shadow-lg"
    : "absolute left-0 top-full z-30 mt-1 max-h-64 min-w-40 overflow-y-auto rounded-md border border-slate-200 bg-white p-1.5 shadow-lg";

  useEffect(() => {
    function closeMenu(event: PointerEvent) {
      if (!dropdownRef.current?.contains(event.target as Node)) {
        window.setTimeout(() => setIsOpen(false), 0); // 새 메뉴 클릭이 끝난 뒤 기존 메뉴를 닫음
      }
    }

    document.addEventListener("pointerdown", closeMenu);
    return () => document.removeEventListener("pointerdown", closeMenu);
  }, []);

  function selectRegion(region: string) {
    onSelect(region);
    setIsOpen(false); // 지역을 고르면 메뉴를 닫음
  }

  return (
    <div className="relative min-w-0" data-region-dropdown ref={dropdownRef}>
      <button className={summaryClassName} onClick={() => setIsOpen((open) => !open)} type="button">
        <span>{regions.length === 0 ? "전체 지역" : "지역 추가"}</span>
        <span aria-hidden="true" className="text-xs text-slate-500">▾</span>
      </button>

      {isOpen && <div className={menuClassName}>
        <button
          className={`block w-full cursor-pointer rounded px-3 py-2 text-left text-sm transition ${
            regions.length === 0
              ? "bg-blue-600 font-semibold text-white"
              : "text-slate-700 hover:bg-blue-50 hover:text-blue-700"
          }`}
          onClick={() => selectRegion("__all__")}
          type="button"
        >
          전체 지역
        </button>

        {REGION_OPTIONS.filter((region) => !regions.includes(region)).map((region) => (
          <button
            className="block w-full cursor-pointer rounded px-3 py-2 text-left text-sm text-slate-700 transition hover:bg-blue-50 hover:text-blue-700"
            key={region}
            onClick={() => selectRegion(region)}
            type="button"
          >
            {region}
          </button>
        ))}
      </div>}
    </div>
  );
}
