"use client";

import { useState } from "react";

type WonInputProps = {
  defaultValue?: number | null;
  label: string;
  name: string;
  placeholder?: string;
};

export function normalizeWonInput(value: string) {
  return value.replace(/\D/g, "");
}

export function formatWonInput(value: string) {
  return value.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

export default function WonInput({
  defaultValue,
  label,
  name,
  placeholder,
}: WonInputProps) {
  const [value, setValue] = useState(() =>
    defaultValue === null || defaultValue === undefined ? "" : String(defaultValue),
  );

  return (
    <label className="block">
      <span className="text-sm font-semibold text-slate-800">{label}</span>
      <div className="relative mt-2">
        <input
          aria-label={label}
          className="h-11 w-full rounded-md border border-slate-300 bg-white px-3.5 pr-9 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
          inputMode="numeric"
          onChange={(event) => setValue(normalizeWonInput(event.target.value))}
          placeholder={placeholder}
          type="text"
          value={formatWonInput(value)}
        />
        <span
          aria-hidden="true"
          className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-xs text-slate-400"
        >
          원
        </span>
      </div>
      <input name={name} type="hidden" value={value} />
    </label>
  );
}
