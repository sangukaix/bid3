"use client";

import type {CompanyMaterialUsage} from "@/types/bid";

export default function CompanyMaterialUsagePanel({usage,onPage}: {
  usage?:CompanyMaterialUsage; onPage:(page:number)=>void;
}) {
  if (!usage) return null;
  return <details className="mt-4 rounded-md border border-slate-200 bg-white p-4">
    <summary className="cursor-pointer font-semibold text-slate-900">
      회사 자료 활용 · 원문 {usage.documents.length}개 · 시각 자료 {usage.used_assets.length}개
    </summary>
    <p className="mt-2 text-sm leading-6 text-slate-600">
      선택한 제안서 양식 안에 회사 자료를 배치했습니다. 원본 파일은 변경하지 않습니다.
      도식과 인포그래픽은 원본 디자인을 유지한 이미지로 들어가며, 주변 제목과 설명은 편집할 수 있습니다.
    </p>
    <p className="mt-2 text-xs leading-5 text-amber-800">
      이미지 안의 과거 수치·발주처·서비스 화면은 현재 사업의 확정 사실이 아닙니다. 현행 적용 범위를 직접 확인하세요.
    </p>
    {usage.documents.length>0 && <ul className="mt-3 space-y-1 text-xs text-slate-600">
      {usage.documents.map(doc=><li key={doc.document_id}>{doc.file_name} · 참고 위치 {doc.pages}개</li>)}
    </ul>}
    <div className="mt-3 space-y-2">{usage.used_assets.map(asset=><article
      key={`${asset.asset_id}-${asset.output_slide_number}`} className="rounded border border-slate-200 p-3 text-sm">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="font-medium text-slate-800">{asset.file_name} · 원문 {asset.source_page}쪽</p>
        <button type="button" onClick={()=>onPage(asset.output_slide_number)}
          className="cursor-pointer rounded border border-slate-300 px-3 py-1 text-blue-700">
          제안서 {asset.output_slide_number}쪽 보기
        </button>
      </div>
      <p className="mt-1 text-xs text-slate-500">{asset.kind==="source_panel" ? "원문 도식·화면 영역" : "원문 이미지"} · {asset.review_note}</p>
      {asset.image_matches_source===false && <p className="mt-1 text-xs text-amber-800">삽입 이미지가 기록된 원문과 달라 다시 확인해야 합니다.</p>}
    </article>)}</div>
    {usage.used_assets.length===0 && <p className="mt-3 text-sm text-slate-600">자동 배치한 시각 자료가 없습니다. 관련 자료와 양식을 확인해 주세요.</p>}
    {usage.failed_files.map((file,i)=><p key={`failed-${i}`} className="mt-2 text-xs text-amber-800">{file.file_name}: {file.reason}</p>)}
    {usage.warnings.map((warning,i)=><p key={`warning-${i}`} className="mt-2 text-xs text-amber-800">{warning}</p>)}
  </details>;
}
