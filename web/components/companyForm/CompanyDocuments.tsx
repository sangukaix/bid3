"use client";

import { useEffect, useRef, useState } from "react";

import { API_BASE_URL } from "@/lib/api";
import type { CompanyDocumentData } from "@/types/company";

const MAX_DOCUMENTS = 10;
const ACCEPTED_DOCUMENTS = ".doc,.docx,.ppt,.pptx,.hwp,.hwpx";

const documentTypes = [
  {
    type: "company_introduction" as const,
    title: "회사 기본 자료",
    description: "회사소개서와 기본 제안서에서 회사 정보, 연혁과 강점을 참고합니다.",
  },
  {
    type: "proposal" as const,
    title: "기존 입찰 제안서",
    description: "과거 제안서에서 수행 실적, 사업 방법론과 검증된 전략을 참고합니다.",
  },
];

type CompanyDocumentsProps = {
  editable?: boolean;
};

function getErrorMessage(data: Record<string, unknown>) {
  if (typeof data.error === "string") return data.error;

  const messages = Object.values(data)
    .flat()
    .filter((value) => typeof value === "string");
  return messages.join(" ") || "문서를 업로드하지 못했습니다.";
}

export default function CompanyDocuments({
  editable = false,
}: CompanyDocumentsProps) {
  const basicFileInputRef = useRef<HTMLInputElement>(null);
  const bidFileInputRef = useRef<HTMLInputElement>(null);
  const [documents, setDocuments] = useState<CompanyDocumentData[]>([]);
  const [basicFile, setBasicFile] = useState<File | null>(null);
  const [bidFile, setBidFile] = useState<File | null>(null);
  const [message, setMessage] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [uploadingType, setUploadingType] = useState<
    CompanyDocumentData["document_type"] | null
  >(null);

  useEffect(() => {
    async function loadDocuments() {
      const token = localStorage.getItem("auth_token");
      if (!token) {
        setIsLoading(false);
        return;
      }

      try {
        const response = await fetch(`${API_BASE_URL}/api/company-documents/`, {
          headers: { Authorization: `Token ${token}` },
        });
        if (!response.ok) throw new Error();

        const data = (await response.json()) as {
          items: CompanyDocumentData[];
        };
        setDocuments(data.items);
      } catch {
        setMessage("등록한 회사 문서를 불러오지 못했습니다.");
      } finally {
        setIsLoading(false);
      }
    }

    loadDocuments();
  }, []);

  async function uploadDocument(
    documentType: CompanyDocumentData["document_type"],
  ) {
    const token = localStorage.getItem("auth_token");
    const selectedFile =
      documentType === "proposal" ? bidFile : basicFile;

    if (!token || !selectedFile) {
      setMessage("업로드할 파일을 선택해 주세요.");
      return;
    }

    const formData = new FormData();
    formData.append("file", selectedFile);
    formData.append("document_type", documentType);

    setMessage("");
    setUploadingType(documentType);

    try {
      const response = await fetch(`${API_BASE_URL}/api/company-documents/`, {
        method: "POST",
        headers: { Authorization: `Token ${token}` },
        body: formData,
      });
      const data = (await response.json().catch(() => ({
        error: "서버 응답을 확인할 수 없습니다.",
      }))) as CompanyDocumentData & Record<string, unknown>;

      if (!response.ok) {
        setMessage(getErrorMessage(data));
        return;
      }

      setDocuments((current) => [data, ...current]);
      if (documentType === "proposal") {
        setBidFile(null);
        if (bidFileInputRef.current) bidFileInputRef.current.value = "";
      } else {
        setBasicFile(null);
        if (basicFileInputRef.current) basicFileInputRef.current.value = "";
      }
      setMessage("회사 문서가 등록되었습니다.");
    } catch {
      setMessage("문서 업로드 서버에 연결할 수 없습니다.");
    } finally {
      setUploadingType(null);
    }
  }

  async function deleteDocument(documentId: number) {
    if (!window.confirm("등록한 문서를 삭제하시겠습니까?")) return;

    const token = localStorage.getItem("auth_token");
    if (!token) return;

    const response = await fetch(
      `${API_BASE_URL}/api/company-documents/${documentId}/`,
      {
        method: "DELETE",
        headers: { Authorization: `Token ${token}` },
      },
    );

    if (response.ok) {
      setDocuments((current) =>
        current.filter((document) => document.id !== documentId),
      );
      setMessage("회사 문서가 삭제되었습니다.");
    } else {
      setMessage("회사 문서를 삭제하지 못했습니다.");
    }
  }

  const reachedLimit = documents.length >= MAX_DOCUMENTS;

  return (
    <section className="app-panel overflow-hidden rounded-lg border">
      <div className="flex items-start justify-between gap-4 border-b border-slate-200 px-6 py-4">
        <div>
          <h2 className="text-base font-bold text-slate-950">회사 자료</h2>
          <p className="mt-1 text-sm text-slate-500">
            AI가 회사의 실적과 수행 역량을 파악할 때 참고하는 자료입니다.
          </p>
        </div>
        <span className="whitespace-nowrap text-xs font-medium text-slate-500">
          {documents.length} / {MAX_DOCUMENTS}
        </span>
      </div>

      {editable && (
        <>
          <div className="divide-y divide-slate-200">
            {documentTypes.map(({ type, title, description }) => {
              const isProposal = type === "proposal";
              const file = isProposal ? bidFile : basicFile;
              const inputRef = isProposal
                ? bidFileInputRef
                : basicFileInputRef;

              return (
                <div
                  className="grid gap-4 px-6 py-5 lg:grid-cols-[220px_minmax(0,1fr)_auto] lg:items-center"
                  key={type}
                >
                  <div>
                    <h3 className="text-sm font-semibold text-slate-900">
                      {title}
                    </h3>
                    <p className="mt-1 text-xs leading-5 text-slate-500">
                      {description}
                    </p>
                  </div>
                  <input
                    accept={ACCEPTED_DOCUMENTS}
                    className="block h-10 w-full cursor-pointer rounded-md border border-slate-300 bg-white text-xs text-slate-600 file:mr-3 file:h-full file:cursor-pointer file:border-0 file:border-r file:border-slate-200 file:bg-slate-50 file:px-3 file:text-xs file:font-normal file:text-slate-700 hover:file:bg-slate-100"
                    disabled={reachedLimit}
                    onChange={(event) => {
                      const selected = event.target.files?.[0] ?? null;
                      if (isProposal) setBidFile(selected);
                      else setBasicFile(selected);
                    }}
                    ref={inputRef}
                    type="file"
                  />
                  <button
                    className="h-10 cursor-pointer rounded-md bg-blue-600 px-4 text-xs font-semibold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-slate-300"
                    disabled={
                      uploadingType !== null || reachedLimit || file === null
                    }
                    onClick={() => uploadDocument(type)}
                    type="button"
                  >
                    {uploadingType === type ? "업로드 중" : "등록"}
                  </button>
                </div>
              );
            })}
          </div>

          <p className="border-t border-slate-200 bg-slate-50/70 px-6 py-3 text-xs leading-5 text-slate-500">
            Word, PowerPoint, HWP, HWPX · 최대 10개
          </p>
        </>
      )}

      <div className={editable ? "border-t border-slate-200" : ""}>
        {isLoading && (
          <p className="px-6 py-8 text-center text-sm text-slate-500">
            등록 문서를 불러오는 중입니다.
          </p>
        )}

        {!isLoading && documents.length === 0 && (
          <p className="px-6 py-8 text-center text-sm text-slate-400">
            등록된 회사 자료가 없습니다.
            {!editable && " 회사정보 수정에서 자료를 등록할 수 있습니다."}
          </p>
        )}

        {!isLoading && documents.length > 0 && (
          <div className="divide-y divide-slate-100">
            {documentTypes.map(({ type, title }) => {
              const items = documents.filter(
                (document) => document.document_type === type,
              );

              return (
                <div
                  className="grid gap-3 px-6 py-4 md:grid-cols-[180px_minmax(0,1fr)]"
                  key={type}
                >
                  <div className="flex items-center gap-2">
                    <h3 className="text-sm font-semibold text-slate-800">
                      {title}
                    </h3>
                    <span className="rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-500">
                      {items.length}
                    </span>
                  </div>
                  {items.length > 0 ? (
                    <div className="space-y-2">
                      {items.map((document) => (
                        <div
                          className="flex min-w-0 items-center justify-between gap-3"
                          key={document.id}
                        >
                          <span className="min-w-0 truncate text-sm text-slate-700">
                            {document.original_name}
                          </span>
                          {editable && (
                            <button
                              className="shrink-0 cursor-pointer text-xs font-semibold text-red-600 hover:text-red-700"
                              onClick={() => deleteDocument(document.id)}
                              type="button"
                            >
                              삭제
                            </button>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-slate-400">등록된 자료가 없습니다.</p>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {message && (
          <p
            className="border-t border-slate-200 bg-slate-50 px-6 py-3 text-sm text-slate-700"
            role="status"
          >
            {message}
          </p>
        )}
      </div>
    </section>
  );
}
