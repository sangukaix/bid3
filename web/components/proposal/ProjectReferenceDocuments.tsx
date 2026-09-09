"use client";

import { useEffect, useRef, useState } from "react";

import { API_BASE_URL } from "@/lib/api";
import type { ProjectReferenceDocumentData } from "@/types/bid";

const ACCEPTED_FILES = ".doc,.docx,.ppt,.pptx,.hwp,.hwpx";

type ProjectReferenceDocumentsProps = {
  bidNtceNo: string;
  disabled?: boolean;
};

function readError(data: Record<string, unknown>) {
  if (typeof data.error === "string") return data.error;
  return (
    Object.values(data).flat().find((value) => typeof value === "string") ??
    "유사 제안서를 등록하지 못했습니다."
  );
}

export default function ProjectReferenceDocuments({
  bidNtceNo,
  disabled = false,
}: ProjectReferenceDocumentsProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [items, setItems] = useState<ProjectReferenceDocumentData[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [message, setMessage] = useState("");
  const [isUploading, setIsUploading] = useState(false);

  useEffect(() => {
    async function loadDocuments() {
      const token = localStorage.getItem("auth_token");
      if (!token) return;
      try {
        const response = await fetch(
          `${API_BASE_URL}/api/bids/${encodeURIComponent(bidNtceNo)}/reference-documents/`,
          { headers: { Authorization: `Token ${token}` } },
        );
        if (!response.ok) return;
        const data = (await response.json()) as {
          items: ProjectReferenceDocumentData[];
        };
        setItems(data.items);
      } catch {
        setMessage("유사 제안서 목록을 불러오지 못했습니다.");
      }
    }

    void loadDocuments();
  }, [bidNtceNo]);

  async function uploadDocument() {
    const token = localStorage.getItem("auth_token");
    if (!token || !file) {
      setMessage("참고할 제안서 파일을 선택해 주세요.");
      return;
    }
    const formData = new FormData();
    formData.append("file", file);
    setIsUploading(true);
    setMessage("");
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/bids/${encodeURIComponent(bidNtceNo)}/reference-documents/`,
        {
          method: "POST",
          headers: { Authorization: `Token ${token}` },
          body: formData,
        },
      );
      const data = (await response.json().catch(() => ({}))) as
        ProjectReferenceDocumentData & Record<string, unknown>;
      if (!response.ok) {
        setMessage(String(readError(data)));
        return;
      }
      setItems((current) => [data, ...current]);
      setFile(null);
      if (inputRef.current) inputRef.current.value = "";
      setMessage("다음 제안서 생성부터 참고합니다.");
    } catch {
      setMessage("유사 제안서 업로드 서버에 연결할 수 없습니다.");
    } finally {
      setIsUploading(false);
    }
  }

  async function deleteDocument(documentId: number) {
    if (!window.confirm("이 프로젝트에서 유사 제안서를 삭제하시겠습니까?")) return;
    const token = localStorage.getItem("auth_token");
    if (!token) return;
    const response = await fetch(
      `${API_BASE_URL}/api/bids/${encodeURIComponent(bidNtceNo)}/reference-documents/${documentId}/`,
      {
        method: "DELETE",
        headers: { Authorization: `Token ${token}` },
      },
    );
    if (!response.ok) {
      setMessage("유사 제안서를 삭제하지 못했습니다.");
      return;
    }
    setItems((current) => current.filter((item) => item.id !== documentId));
    setMessage("유사 제안서를 삭제했습니다.");
  }

  const reachedLimit = items.length >= 3;

  return (
    <section className="border-b border-slate-200 py-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h3 className="text-sm font-bold text-slate-900">유사 제안서 참고</h3>
          <p className="mt-1 text-xs leading-5 text-slate-500">
            유사 사업 제안서를 추가하면 실적·방법론·표현 방식을 이 프로젝트에만 참고합니다.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <input
            accept={ACCEPTED_FILES}
            className="block max-w-[260px] text-xs text-slate-500 file:mr-2 file:cursor-pointer file:rounded-md file:border file:border-slate-300 file:bg-white file:px-3 file:py-2 file:text-xs file:text-slate-700 hover:file:bg-slate-50"
            disabled={disabled || reachedLimit || isUploading}
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            ref={inputRef}
            type="file"
          />
          <button
            className="cursor-pointer rounded-md border border-blue-200 px-3 py-2 text-xs font-semibold text-blue-700 hover:bg-blue-50 disabled:cursor-not-allowed disabled:border-slate-200 disabled:text-slate-300"
            disabled={disabled || reachedLimit || isUploading || !file}
            onClick={() => void uploadDocument()}
            type="button"
          >
            {isUploading ? "등록 중" : "등록"}
          </button>
        </div>
      </div>

      {items.length > 0 && (
        <ul className="mt-3 flex flex-wrap gap-2">
          {items.map((item) => (
            <li
              className="flex max-w-full items-center gap-2 rounded-md bg-slate-100 px-3 py-2 text-xs text-slate-700"
              key={item.id}
            >
              <span className="max-w-[280px] truncate">{item.original_name}</span>
              <button
                aria-label={`${item.original_name} 삭제`}
                className="cursor-pointer text-slate-400 hover:text-red-600"
                disabled={disabled}
                onClick={() => void deleteDocument(item.id)}
                title="삭제"
                type="button"
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      )}
      {message && <p className="mt-2 text-xs text-slate-500">{message}</p>}
    </section>
  );
}
