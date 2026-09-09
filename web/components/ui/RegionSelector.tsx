"use client";

import RegionDropdown from "@/components/ui/RegionDropdown";

type RegionSelectorProps = {
  regions: string[];
  onChange: (regions: string[]) => void;
  name?: string;
  label?: string;
  description?: string;
};

export function parseRegions(value: string) {
  return value
    .split(",")
    .map((region) => region.trim())
    .filter(Boolean);
}

export default function RegionSelector({
  regions,
  onChange,
  name,
  label = "희망 지역",
  description = "여러 지역을 차례대로 추가할 수 있습니다.",
}: RegionSelectorProps) {
  function addRegion(region: string) {
    if (region === "__all__") {
      onChange([]); // 전체 지역을 선택하면 저장할 지역 목록을 비움
      return;
    }

    if (!region || regions.includes(region)) {
      return;
    }

    onChange([...regions, region]); // 지역을 고르는 즉시 목록에 추가
  }

  function removeRegion(region: string) {
    onChange(regions.filter((item) => item !== region));
  }

  return (
    <div>
      <span className="text-sm font-semibold text-slate-800">{label}</span>

      <div className="mt-2">
        <RegionDropdown onSelect={addRegion} regions={regions} variant="field" />
      </div>

      <div className="mt-3 flex min-h-11 flex-wrap items-center gap-2 rounded-md border border-slate-200 bg-slate-50 p-2">
        {regions.map((region) => (
          <span
            className="inline-flex items-center gap-1 rounded-md bg-emerald-50 px-2.5 py-1.5 text-sm font-semibold text-emerald-700"
            key={region}
          >
            {region}
            <button
              aria-label={`${region} 지역 삭제`}
              className="h-5 w-5 cursor-pointer text-base leading-none text-emerald-500 hover:text-emerald-800"
              onClick={() => removeRegion(region)}
              title="지역 삭제"
              type="button"
            >
              ×
            </button>
          </span>
        ))}

        {regions.length === 0 && (
          <span className="rounded-md bg-emerald-50 px-2.5 py-1.5 text-sm font-semibold text-emerald-700">
            전체 지역
          </span>
        )}
      </div>

      {name && <input name={name} readOnly type="hidden" value={regions.join(", ")} />}
      <p className="mt-2 text-xs text-slate-500">{description}</p>
    </div>
  );
}
