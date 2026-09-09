"use client"; // 제안서 미리보기와 AI비서를 전체 화면에 함께 표시

import type { ReactNode } from "react";
import { useEffect, useState } from "react";

type ProposalPreviewModalProps = {
  previewUrl: string;
  slideCount: number;
  renderAssistant: (selectedPage: number) => ReactNode;
  onClose: () => void;
};

export default function ProposalPreviewModal({
  previewUrl,
  slideCount,
  renderAssistant,
  onClose,
}: ProposalPreviewModalProps) {
  const pageCount = Math.max(slideCount, 1);
  const [selectedPage, setSelectedPage] = useState(1);

  useEffect(() => {
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden"; // 팝업 뒤 페이지의 스크롤을 잠금

    function closeWithEscape(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }

    window.addEventListener("keydown", closeWithEscape);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", closeWithEscape);
    };
  }, [onClose]);

  return (
    <div
      aria-label="제안서 전체 화면 미리보기"
      aria-modal="true"
      className="fixed inset-0 z-[100] bg-slate-950/55 p-3 backdrop-blur-[1px] sm:p-5"
      role="dialog"
    >
      <div className="flex h-full min-h-0 flex-col overflow-hidden rounded-lg border border-slate-300 bg-slate-100 shadow-2xl">
        <header className="flex h-14 shrink-0 items-center justify-between border-b border-slate-200 bg-white px-4">
          <div className="min-w-0">
            <h2 className="truncate text-sm font-bold text-slate-950">
              제안서 전체 화면 미리보기
            </h2>
            <p className="text-xs text-slate-500">
              {selectedPage} / {pageCount}쪽
            </p>
          </div>
          <button
            aria-label="전체 화면 미리보기 닫기"
            className="flex h-9 w-9 cursor-pointer items-center justify-center rounded-md text-xl text-slate-500 hover:bg-slate-100 hover:text-slate-950"
            onClick={onClose}
            title="닫기"
            type="button"
          >
            ×
          </button>
        </header>

        <div className="grid min-h-0 flex-1 grid-cols-1 lg:grid-cols-[54px_minmax(0,1fr)_320px]">
          <aside className="hidden min-h-0 overflow-y-auto border-r border-slate-200 bg-white px-1 py-2 lg:block">
            <div className="grid grid-cols-1 gap-1">
              {Array.from({ length: pageCount }, (_, index) => {
                const page = index + 1;
                return (
                  <button
                    aria-label={`${page}쪽 보기`}
                    className={`h-8 cursor-pointer rounded border text-[11px] ${
                      selectedPage === page
                        ? "border-blue-500 bg-blue-50 font-semibold text-blue-700"
                        : "border-slate-200 bg-white text-slate-600 hover:border-blue-300 hover:bg-slate-50"
                    }`}
                    key={page}
                    onClick={() => setSelectedPage(page)}
                    type="button"
                  >
                    {page}
                  </button>
                );
              })}
            </div>
          </aside>

          <main className="relative flex min-h-0 min-w-0 flex-col bg-slate-200">
            <div className="min-h-0 flex-1 p-1">
              <iframe
                className="h-full min-h-[420px] w-full bg-white"
                key={selectedPage}
                src={`${previewUrl}#page=${selectedPage}&view=FitH&toolbar=0&navpanes=0&scrollbar=1`}
                title={`제안서 ${selectedPage}쪽 미리보기`}
              />
            </div>
          </main>

          <aside className="hidden min-h-0 overflow-hidden border-l border-slate-200 bg-white lg:block">
            {renderAssistant(selectedPage)}
          </aside>
        </div>
      </div>
    </div>
  );
}
