"use client";

import { useEffect, useRef, useState } from "react";

const BUSINESS_TYPES = [
  { label: "전체", value: "" },
  { label: "공사", value: "공사" },
  { label: "용역", value: "용역" },
  { label: "물품", value: "물품" },
];

type BusinessTypeDropdownProps = {
  value: string;
  onChange: (value: string) => void;
};

export default function BusinessTypeDropdown({
  value,
  onChange,
}: BusinessTypeDropdownProps) {
  const dropdownRef = useRef<HTMLDivElement>(null);
  const [isOpen, setIsOpen] = useState(false);
  const selectedLabel = BUSINESS_TYPES.find((item) => item.value === value)?.label ?? "전체";

  useEffect(() => {
    function closeMenu(event: PointerEvent) {
      if (!dropdownRef.current?.contains(event.target as Node)) {
        window.setTimeout(() => setIsOpen(false), 0); // 새 메뉴 클릭이 끝난 뒤 기존 메뉴를 닫음
      }
    }

    document.addEventListener("pointerdown", closeMenu);
    return () => document.removeEventListener("pointerdown", closeMenu);
  }, []);

  function selectType(nextValue: string) {
    onChange(nextValue);
    setIsOpen(false);
  }

  return (
    <div className="relative" data-business-type-dropdown ref={dropdownRef}>
      <button
        className="flex h-10 w-full cursor-pointer items-center justify-between rounded-md border border-slate-300 bg-white px-3 text-sm text-slate-700 outline-none transition hover:border-blue-400"
        onClick={() => setIsOpen((open) => !open)}
        type="button"
      >
        <span>{selectedLabel}</span>
        <span aria-hidden="true" className="text-xs text-slate-500">▾</span>
      </button>

      {isOpen && <div className="absolute left-0 top-full z-40 mt-1 min-w-40 overflow-hidden rounded-md border border-slate-200 bg-white p-1.5 shadow-lg">
        {BUSINESS_TYPES.map((item) => (
          <button
            className={`block w-full cursor-pointer rounded px-3 py-2 text-left text-sm transition ${
              item.value === value
                ? "bg-blue-600 font-semibold text-white"
                : "text-slate-700 hover:bg-blue-50 hover:text-blue-700"
            }`}
            key={item.label}
            onClick={() => selectType(item.value)}
            type="button"
          >
            {item.label}
          </button>
        ))}
      </div>}
    </div>
  );
}
